"""
LightGBM 模型加載器 - 加載和管理 LightGBM 模型
支持瑜伽姿勢預測
"""

from pathlib import Path
import joblib
import pandas as pd
from lightgbm import LGBMClassifier
import numpy as np
from typing import Tuple
from config.settings import LIGHTGBM_MODEL_PATH


class LightGBMLoader:
    """
    LightGBM 模型加載器
    - 加載設定的姿勢分類模型文件
    - 提供模型推理接口
    - 返回姿勢預測和置信度
    """
    
    # 支援姿勢；實例載入後依模型 classes_ 排序
    POSE_CLASSES_ZH = [
        "下犬式",      # 0
        "女神式",      # 1
        "平板式",      # 2
        "戰士二式",    # 3
        "樹式"         # 4
    ]
    
    POSE_CLASSES_EN = [
        "Downward Dog",   # 0
        "Goddess Pose",   # 1
        "Plank Pose",     # 2
        "Warrior II",     # 3
        "Tree Pose"       # 4
    ]
    
    def __init__(self, model_path: str = LIGHTGBM_MODEL_PATH):
        """
        初始化 LightGBM 加載器
        
        Args:
            model_path: 模型文件路徑 (相對或絕對)
        """
        self.model_path = Path(model_path)
        if not self.model_path.is_absolute():
            self.model_path = Path(__file__).resolve().parents[1] / self.model_path
        self.model = None
        self.is_loaded = False
        self._load_model()
    
    LABELS_ZH = {
        "downdog": "下犬式", "goddess": "女神式", "plank": "平板式",
        "tree": "樹式", "warrior2": "戰士二式",
    }

    def _load_model(self):
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        try:
            from utils.feature_extractor import FeatureExtractor
            from utils.pose_translator import PoseTranslator
            model = joblib.load(self.model_path)
            if not isinstance(model, LGBMClassifier):
                raise ValueError("Expected a fitted LGBMClassifier")
            labels = list(model.classes_)
            feature_names = list(model.feature_name_)
            if len(labels) != 5 or set(labels) != set(self.LABELS_ZH):
                raise ValueError(f"Unsupported model classes: {labels}")
            names = FeatureExtractor.feature_names()
            if (feature_names != names + ["knee_angle_diff_deg"]
                    or model.n_features_in_ != len(names) + 1):
                raise ValueError("Expected the 78-feature anglediff model schema")
            self.input_feature_count = len(names)
            self.model = model
            self.class_labels = labels
            self.feature_names = feature_names
            self.POSE_CLASSES_ZH = [self.LABELS_ZH[label] for label in labels]
            self.POSE_CLASSES_EN = [PoseTranslator.translate_to_english(pose) for pose in self.POSE_CLASSES_ZH]
            self.is_loaded = True
        except Exception as exc:
            raise RuntimeError(f"Failed to load pose model: {exc}") from exc

    def predict(self, features: np.ndarray) -> Tuple[str, str, float]:
        """
        使用 LightGBM 模型進行預測
        
        Args:
            features: 提取的特徵向量，形狀 (77,) 或 (1, 77)
                     包含 23 個關鍵點的 xyz 座標 + 8 個角度特徵
            
        Returns:
            Tuple[str, str, float]: (主姿勢_中文, 子姿勢_中文, 置信度)
                                   子姿勢在此模型中與主姿勢相同
                                   置信度範圍 [0, 1]
        """
        if not self.is_loaded:
            raise RuntimeError(
                "Model not loaded. Check that the configured model exists and is valid."
            )
        
        try:
            # 確保特徵是 2D 陣列 (1, 77)
            features = np.asarray(features, dtype=float)
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # 進行預測，返回每個類的預測概率
            # LGBMClassifier 的 predict_proba() 返回形狀 (n_samples, n_classes)
            if features.shape != (1, self.input_feature_count) or not np.isfinite(features).all():
                raise ValueError("Expected one finite feature vector with shape (77,) or (1, 77)")
            # The final two base features are the left and right knee angles.
            knee_diff = np.abs(features[:, -2] - features[:, -1])
            model_features = np.column_stack((features, knee_diff))
            frame = pd.DataFrame(model_features, columns=self.feature_names)
            predictions = np.asarray(self.model.predict_proba(frame), dtype=float)
            if (predictions.shape != (1, len(self.model.classes_))
                    or not np.isfinite(predictions).all()
                    or np.any(predictions < 0) or np.any(predictions > 1)
                    or not np.isclose(predictions.sum(), 1)):
                raise ValueError("Model returned invalid class probabilities")
            
            # 提取第一個樣本的預測結果
            pred_probs = predictions[0]  # 形狀 (5,)，每個類的概率
            
            # 找到置信度最高的類
            max_idx = int(np.argmax(pred_probs))
            max_prob = float(pred_probs[max_idx])
            
            # 正規化到 [0, 1]，確保 sum = 1
            if np.sum(pred_probs) > 0:
                confidence = max_prob / np.sum(pred_probs)
            else:
                confidence = 0.0
            
            # 返回姿勢名稱 (中文) 和置信度
            # 子姿勢與主姿勢相同 (此模型無細粒度分類)
            pose_zh = self.LABELS_ZH[self.class_labels[max_idx]]
            
            return pose_zh, pose_zh, confidence
            
        except Exception as e:
            raise RuntimeError(f"Prediction failed: {e}")
