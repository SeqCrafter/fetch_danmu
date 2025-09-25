import reflex as rx
from ..template import template
from urllib.parse import unquote_plus
from ..components.artplayer import artplayer_component
import os


class PreviewState(rx.State):
    play_url: str = ""
    danmaku_url: str = ""
    loading: bool = True
    show_code: bool = False
    rq_url: str = ""
    douban_id: str = ""
    episode_number: str = ""
    code: str = ""
    current_host: str = ""

    @rx.event
    def get_code(self) -> None:
        self.code = f"curl {self.current_host}/api/douban_id?douban_id={self.douban_id}&episode_number={self.episode_number}"
        self.show_code = not self.show_code

    @rx.event
    def unmount_clean(self) -> None:
        self.reset()

    @rx.event
    def load_json_data(self) -> None:
        args = self.router.url.query_parameters
        url = args.get("url", "")
        url = unquote_plus(url)
        douban_id = args.get("douban_id", "")
        episode_number = args.get("episode_number", "")
        self.play_url = url
        self.douban_id = douban_id
        self.episode_number = episode_number

        schema = self.router.url.scheme
        if schema == "https":
            ## using domain
            current_host = self.router.url.origin
        else:
            ## get api_url from environment variable:REFLEX_API_URL
            current_host = os.getenv("REFLEX_API_URL")
        self.current_host = current_host
        self.danmaku_url = f"{self.current_host}/api/douban_id?douban_id={self.douban_id}&episode_number={self.episode_number}"
        self.loading = False


def code_block(code: str, language: str):
    return rx.box(
        rx._x.code_block(
            code,
            language=language,
            class_name="code-block max-h-[450px] overflow-y-auto",
            can_copy=True,
            border_radius="12px",
        ),
        class_name="relative mb-4",
        width="100%",
    )


def data_view() -> rx.Component:
    return rx.flex(
        artplayer_component(
            url=PreviewState.play_url,
            danmaku_url=PreviewState.danmaku_url,
            width="850px",
            height="480px",
            on_unmount=PreviewState.unmount_clean,
        ),
        rx.hstack(
            rx.button(
                rx.icon(tag="arrow-left"),
                "返回",
                on_click=rx.call_script("window.history.back()"),
                color_scheme="gray",
                variant="outline",
                radius="large",
                width="85px",
                height="40px",
                style={"cursor": "pointer"},
            ),
            rx.button(
                rx.icon(
                    tag="code-xml",
                ),
                "获取命令",
                on_click=PreviewState.get_code,
                color_scheme="iris",
                variant="outline",
                radius="large",
                width="140px",
                height="40px",
                style={"cursor": "pointer"},
            ),
            spacing="4",
        ),
        spacing="4",
        direction="column",
        width="100%",
    )


@rx.page(route="/preview", on_load=PreviewState.load_json_data, title="弹幕预览")
@template
def preview() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.flex(
                rx.heading("弹幕播放器预览", size="6"),
            ),
            rx.flex(
                rx.text(
                    "基于ArtPlayer的弹幕播放器演示弹幕功能!视频接口不稳定,弹幕服务部署在国外的VPS上, 建议自行部署服务以获得更好的体验!",
                    size="4",
                    color_scheme="gray",
                ),
            ),
            rx.cond(
                PreviewState.loading,
                rx.center(
                    rx.vstack(
                        rx.spinner(color="red", size="3", class_name="animate-spin"),
                        rx.text(
                            "正在加载数据...",
                            class_name="text-gray-600 font-medium mt-3",
                        ),
                        align="center",
                        spacing="3",
                    ),
                    class_name="py-20",
                    width="100%",
                ),
                data_view(),
            ),
            rx.flex(
                rx.cond(
                    PreviewState.show_code,
                    code_block(PreviewState.code, "bash"),
                    rx.box(),
                ),
                width="100%",
            ),
            width="100%",
            spacing="3",
            class_name="mt-6",
        ),
        width="100%",
        size="3",
        class_name="min-h-[calc(100vh-67px-145px)]",
    )
