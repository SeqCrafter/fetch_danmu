from tortoise.models import Model
from tortoise import fields


class Video(Model):
    id = fields.IntField(primary_key=True)
    douban_id = fields.CharField(max_length=50, unique=True, description="豆瓣ID")
    name = fields.CharField(max_length=255, description="剧名")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    # 反向关系类型提示，用于访问关联的播放链接
    playlinks: fields.ReverseRelation["PlayLink"]

    class Meta:  # type: ignore
        table = "video"
        table_description = "视频信息表"

    def __str__(self):
        return f"{self.name} ({self.douban_id})"


class PlayLink(Model):
    id = fields.IntField(primary_key=True)
    episode = fields.CharField(max_length=50, description="第几集")
    link = fields.TextField(description="播放链接")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    # 外键关联到Video表，一个视频对应多个播放链接
    video: fields.ForeignKeyRelation[Video] = fields.ForeignKeyField(
        "models.Video",
        related_name="playlinks",
        on_delete=fields.OnDelete.CASCADE,
        description="关联的视频",
    )

    class Meta:  # type: ignore
        table = "playlink"
        table_description = "播放链接表"
        # 确保同一个视频的集数不重复
        unique_together = (("video", "episode"),)

    def __str__(self):
        return f"第{self.episode}集 - {self.video.name}"
