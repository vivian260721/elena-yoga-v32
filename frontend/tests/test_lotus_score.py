import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.lotus_score import render_lotus_row


class LotusScoreTests(unittest.TestCase):
    def test_table_scores_use_full_half_and_empty_images(self):
        for score in (0, 1, 2, 3, 3.5, 4, 4.5, 5):
            with self.subTest(score=score):
                html = render_lotus_row(score)
                full = int(score)
                half = int(score % 1 != 0)
                self.assertEqual(html.count('part_1.png'), full)
                self.assertEqual(html.count('part_2.png'), half)
                self.assertEqual(html.count('part_3.png'), 5 - full - half)
                self.assertIn(f'{score:g} / 5', html)
        self.assertTrue((Path(__file__).resolve().parents[1] /
                         'static/images/lotus_parts/part_2.png').is_file())
