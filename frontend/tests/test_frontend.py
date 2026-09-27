"""Regression tests using real NiceGUI elements and mocked media/API boundaries."""
import base64
import copy
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import api_client
from services.video_timeline import frame_view


def prediction(name):
    return {"pose": name, "feedback": name, "suggestions": [name],
            "rating": {"score": 4, "encouragement": "Good"},
            "original_image": "data:image/png;base64,AA==",
            "skeleton_image": "data:image/png;base64,AA=="}


def video_frames():
    return [
        {"timestamp_seconds": 0, "prediction": None, "reason": "No person",
         "original_image": "data:image/png;base64,AA==", "is_feedback_frame": False},
        {"timestamp_seconds": .5, "prediction": prediction("first"), "is_feedback_frame": True},
        {"timestamp_seconds": 1, "prediction": prediction("current"), "is_feedback_frame": False},
        {"timestamp_seconds": 1.5, "prediction": None, "reason": "Occluded", "is_feedback_frame": False},
        {"timestamp_seconds": 2.5, "prediction": prediction("next"), "is_feedback_frame": True},
    ]


class TimelineTests(unittest.TestCase):
    def test_seeking_preserves_scheduled_feedback_and_current_image(self):
        frames = video_frames()
        original = copy.deepcopy(frames)
        self.assertEqual(frame_view(frames, 4)[0]["feedback"], "next")
        result, timestamp = frame_view(frames, 2)
        self.assertEqual(result["pose"], "current")
        self.assertEqual(result["feedback"], "first")
        self.assertEqual(result["suggestions"], ["first"])
        self.assertIn("0.50", timestamp)
        self.assertEqual(frames, original)

    def test_unavailable_frames_replace_feedback_and_hide_pose(self):
        result, _ = frame_view(video_frames(), 3)
        self.assertIsNone(result["rating"])
        self.assertIsNone(result["reason"])
        self.assertEqual(result["pose"], "")
        self.assertEqual(result["feedback"], "Occluded")
        result, timestamp = frame_view(video_frames(), 0)
        self.assertEqual(result["suggestions"], [])
        self.assertEqual(timestamp, "")

    def test_empty_and_single_frame(self):
        with self.assertRaises(ValueError):
            frame_view([], 0)
        self.assertEqual(frame_view(video_frames()[1:2], 9)[0]["pose"], "first")


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_failure_never_returns_a_prediction(self):
        def offline(request):
            raise httpx.ConnectError("Backend unavailable", request=request)
        client = httpx.AsyncClient(transport=httpx.MockTransport(offline))
        with patch.object(api_client.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(httpx.ConnectError):
                await api_client.analyze_media(b"photo", "photo.jpg", False)

    async def test_multipart_bytes_endpoints_and_timeout(self):
        real_client = httpx.AsyncClient
        for is_video, endpoint in [(False, "/api/predict"), (True, "/api/predict-video")]:
            with self.subTest(is_video=is_video):
                def respond(request):
                    self.assertEqual(request.url.path, endpoint)
                    self.assertIn(b'filename="capture.bin"', request.content)
                    self.assertIn(b"media-payload", request.content)
                    self.assertEqual(request.extensions["timeout"]["read"], 180)
                    return httpx.Response(200, json={"ok": True})
                client = real_client(transport=httpx.MockTransport(respond), timeout=180)
                with patch.object(api_client.httpx, "AsyncClient", return_value=client):
                    self.assertEqual(await api_client.analyze_media(
                        b"media-payload", "capture.bin", is_video), {"ok": True})

    async def test_backend_error_detail(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(413, json={"detail": "Too large"})))
        with patch.object(api_client.httpx, "AsyncClient", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "Too large"):
                await api_client.analyze_media(b"x", "x.jpg", False)

    def test_environment_priority_and_legacy_fallback(self):
        try:
            for env, expected in [({}, "http://localhost:8000"),
                                  ({"BACKEND_API_URL": "http://legacy/"}, "http://legacy"),
                                  ({"BACKEND_API_URL": "http://legacy/", "YOGA_API_BASE_URL": "http://new/"}, "http://new")]:
                with patch.dict(os.environ, env, clear=True):
                    importlib.reload(api_client)
                    self.assertEqual(api_client.API_BASE_URL, expected)
        finally:
            importlib.reload(api_client)


class PageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from nicegui import Client, ui
        import main
        self.ui, self.main = ui, main
        self.client = Client(ui.page("/test"))
        self.callbacks = {}
        self.buttons = {}
        original_upload = main.components.build_upload_section
        original_button = ui.button

        def upload(**kwargs):
            self.callbacks.update(kwargs)
            return original_upload(**kwargs)

        def button(text="", **kwargs):
            if kwargs.get("on_click"):
                self.buttons[text] = kwargs["on_click"]
            return original_button(text, **kwargs)

        with self.client, patch.object(main.components, "build_upload_section", side_effect=upload), \
                patch.object(ui, "button", side_effect=button), patch.object(ui, "timer"):
            await main.practice_page()

    async def asyncTearDown(self):
        self.client.delete()

    def labels(self):
        return [getattr(element, "text", "") for element in self.client.elements.values()]

    async def test_upload_video_seek_then_photo_resets_timeline(self):
        frames = video_frames()
        mock_api = AsyncMock(return_value={"frames": frames, "analyzed_frames": 3})
        with self.client, patch.object(api_client, "analyze_media", mock_api):
            upload = next(e for e in self.client.elements.values() if isinstance(e, self.ui.upload))
            event = SimpleNamespace(file=SimpleNamespace(
                read=AsyncMock(return_value=b"video"), name="clip.MP4", content_type="application/octet-stream"))
            await upload._upload_handlers[0](event)
            await self.callbacks["on_submit"]()
            self.assertTrue(mock_api.call_args.kwargs["is_video"])
            self.assertIn("No person", self.labels())
            slider = next(e for e in self.client.elements.values() if isinstance(e, self.ui.slider))
            self.assertEqual(slider.props["max"], 4)
            slider.value = 4
            self.assertIn("next", self.labels())
            slider = next(e for e in self.client.elements.values() if isinstance(e, self.ui.slider))
            slider.value = 2
            self.assertIn("current", self.labels())
            self.assertIn("first", self.labels())
            slider = next(e for e in self.client.elements.values() if isinstance(e, self.ui.slider))
            slider.value = 3
            self.assertIn("Occluded", self.labels())
            mock_api.return_value = prediction("photo")
            await self.callbacks["on_captured"](b"photo", "photo.jpg", "image/jpeg")
            self.assertFalse(any(isinstance(e, self.ui.slider) for e in self.client.elements.values()))
            self.assertIn("photo", self.labels())

    async def test_camera_photo_and_recording_use_three_argument_callback(self):
        mock_api = AsyncMock(return_value=prediction("photo"))
        payload = "data:image/jpeg;base64," + base64.b64encode(b"camera").decode()
        with self.client, patch.object(api_client, "analyze_media", mock_api), \
                patch.object(self.ui, "run_javascript", AsyncMock(return_value=payload)):
            await self.buttons["拍照"]()
            self.assertEqual(mock_api.call_args.kwargs["file_bytes"], b"camera")
            self.assertFalse(mock_api.call_args.kwargs["is_video"])
            mock_api.return_value = {"frames": video_frames(), "analyzed_frames": 3}
            await self.buttons["開始錄影"]()
            await self.buttons["開始錄影"]()
            self.assertTrue(mock_api.call_args.kwargs["is_video"])
            self.assertEqual(mock_api.call_args.kwargs["filename"], "camera_capture.webm")


if __name__ == "__main__":
    unittest.main()
