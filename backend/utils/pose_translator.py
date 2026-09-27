"""
瑜伽姿勢翻譯器 - 中文 ↔ 英文互轉
"""

from typing import Dict, Optional


class PoseTranslator:
    """
    瑜伽姿勢中英翻譯管理
    - 提供中文轉英文的翻譯
    - 提供英文轉中文的翻譯
    - 支持查詢和驗證
    """
    
    # 姿勢翻譯對應表
    POSE_TRANSLATIONS = {
        # 中文 → 英文
        "戰士二式": "Warrior II Pose",
        "下犬式": "Downward Dog Pose",
        "女神式": "Goddess Pose",
        "平板式": "Plank Pose",
        "樹式": "Tree Pose",
    }
    
    # 英文 → 中文反向映射
    REVERSE_TRANSLATIONS = {v: k for k, v in POSE_TRANSLATIONS.items()}
    
    def __init__(self):
        """初始化翻譯器"""
        pass
    
    @classmethod
    def translate_to_english(cls, pose_name_zh: str) -> Optional[str]:
        """
        將中文姿勢名稱翻譯為英文
        
        Args:
            pose_name_zh: 中文姿勢名稱
            
        Returns:
            英文姿勢名稱，如果不存在返回 None
        """
        return cls.POSE_TRANSLATIONS.get(pose_name_zh)
    
    @classmethod
    def translate_to_chinese(cls, pose_name_en: str) -> Optional[str]:
        """
        將英文姿勢名稱翻譯為中文
        
        Args:
            pose_name_en: 英文姿勢名稱
            
        Returns:
            中文姿勢名稱，如果不存在返回 None
        """
        return cls.REVERSE_TRANSLATIONS.get(pose_name_en)
    
    @classmethod
    def get_all_poses(cls) -> Dict[str, str]:
        """
        獲取所有姿勢的翻譯對應
        
        Returns:
            Dict: {中文: 英文} 的字典
        """
        return cls.POSE_TRANSLATIONS.copy()
    
    @classmethod
    def get_pose_names_zh(cls) -> list:
        """獲取所有中文姿勢名稱"""
        return list(cls.POSE_TRANSLATIONS.keys())
    
    @classmethod
    def get_pose_names_en(cls) -> list:
        """獲取所有英文姿勢名稱"""
        return list(cls.POSE_TRANSLATIONS.values())
    
    @classmethod
    def is_valid_pose_zh(cls, pose_name: str) -> bool:
        """檢查中文姿勢名稱是否有效"""
        return pose_name in cls.POSE_TRANSLATIONS
    
    @classmethod
    def is_valid_pose_en(cls, pose_name: str) -> bool:
        """檢查英文姿勢名稱是否有效"""
        return pose_name in cls.REVERSE_TRANSLATIONS


# 使用示例
if __name__ == "__main__":
    # 中文轉英文
    print(PoseTranslator.translate_to_english("戰士二式"))  # → Warrior II Pose
    
    # 英文轉中文
    print(PoseTranslator.translate_to_chinese("Downward Dog Pose"))  # → 下犬式
    
    # 獲取所有翻譯
    print(PoseTranslator.get_all_poses())
    
    # 驗證
    print(PoseTranslator.is_valid_pose_zh("樹式"))  # → True
