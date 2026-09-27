"""
標準化處理器 - 將 landmarks 進行標準化/正規化
根據 MediaPipe 的 normalize_keypoints 規則
"""

import numpy as np
from typing import Tuple


class Normalizer:
    """
    Landmarks 標準化處理 (根據 MediaPipe 標準)
    - 處理可見度/置信度
    - 智能中心選擇（髖部 → 肩部 → 全身）
    - 考慮軀幹大小的動態縮放
    - z 軸也進行正規化
    """
    
    # MediaPipe 標誌點索引
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    
    # 常數
    CONFIDENCE_THRESHOLD = 0.25
    TORSO_MULTIPLIER = 2.5
    
    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD, 
                 torso_multiplier: float = TORSO_MULTIPLIER):
        """
        初始化標準化器
        
        Args:
            confidence_threshold: 可見度閾值 (0-1)
            torso_multiplier: 軀幹乘數，用於計算身體尺度
        """
        self.confidence_threshold = confidence_threshold
        self.torso_multiplier = torso_multiplier
    
    def normalize(self, 
                  landmarks: np.ndarray, 
                  visibility: np.ndarray = None) -> Tuple[np.ndarray, str]:
        """
        標準化 landmarks
        
        Args:
            landmarks: 原始 landmarks 數組 (33, 3) - [x, y, z]
            visibility: 可見度陣列 (33,) - 若無則假設所有點都可見
            
        Returns:
            Tuple[np.ndarray, str]: (標準化後的 landmarks, 中心類型)
        """
        # Step 1: 檢查形狀
        if landmarks.shape[0] != 33 or landmarks.shape[1] != 3:
            raise ValueError(f"Expected shape (33, 3), got {landmarks.shape}")
        
        # Step 2: 處理可見度
        normalized = landmarks.astype(np.float32, copy=True)
        
        if visibility is None:
            # 若無可見度信息，假設所有點都可見
            visibility = np.ones(33, dtype=np.float32)
        
        # Step 3: 確定哪些點可靠
        reliable = visibility >= self.confidence_threshold
        
        # 如果沒有可靠的點，返回全零
        if not reliable.any():
            normalized[:, :] = 0.0
            return normalized, "none"
        
        # Step 4: 智能選擇中心點
        xy = normalized[:, :2]
        z = normalized[:, 2]
        
        hips_reliable = reliable[self.LEFT_HIP] and reliable[self.RIGHT_HIP]
        shoulders_reliable = reliable[self.LEFT_SHOULDER] and reliable[self.RIGHT_SHOULDER]
        
        if hips_reliable:
            # 優先使用髖部中心（最穩定）
            center = (xy[self.LEFT_HIP] + xy[self.RIGHT_HIP]) / 2.0
            center_z = (z[self.LEFT_HIP] + z[self.RIGHT_HIP]) / 2.0
            center_type = "hip_center"
        elif shoulders_reliable:
            # 其次使用肩部中心
            center = (xy[self.LEFT_SHOULDER] + xy[self.RIGHT_SHOULDER]) / 2.0
            center_z = (z[self.LEFT_SHOULDER] + z[self.RIGHT_SHOULDER]) / 2.0
            center_type = "shoulder_center"
        else:
            # 最後使用全身平均
            center = xy[reliable].mean(axis=0)
            center_z = z[reliable].mean()
            center_type = "full_body_center"
        
        # Step 5: 計算身體尺度
        body_radius = np.linalg.norm(xy[reliable] - center, axis=1).max()
        
        if hips_reliable and shoulders_reliable:
            # 考慮軀幹大小
            shoulder_center = (xy[self.LEFT_SHOULDER] + xy[self.RIGHT_SHOULDER]) / 2.0
            hip_center = (xy[self.LEFT_HIP] + xy[self.RIGHT_HIP]) / 2.0
            torso_size = np.linalg.norm(shoulder_center - hip_center)
            pose_scale = max(body_radius, self.torso_multiplier * torso_size)
        else:
            pose_scale = body_radius
        
        # Step 6: 檢查縮放因子是否過小
        if pose_scale <= np.finfo(np.float32).eps:
            normalized[:, :] = 0.0
            return normalized, "none"
        
        # Step 7: 應用中心化和縮放
        normalized[:, :2] = (xy - center) / pose_scale
        normalized[:, 2] = (z - center_z) / pose_scale
        
        # Step 8: 不可靠的點置為零
        normalized[~reliable, :] = 0.0
        
        return normalized, center_type
