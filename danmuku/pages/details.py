import reflex as rx
from ..template import template
from ..provides.mtzy import get_vod_details
from typing import Any, Dict
from ..components.media_details import media_details_component


class DetailsState(rx.State):
    vod_details: Dict[str, Any] = {}
    loading: bool = True

    @rx.event
    def load_json_data(self) -> None:
        args = self.router.url.query_parameters
        vod_id = args.get("vod_id", "")
        if vod_id:
            self.vod_details = get_vod_details(int(vod_id))
            self.loading = False
        else:
            return rx.redirect("/")

    @rx.event
    def unmount_clean(self) -> None:
        self.reset()


@rx.page(route="/details", on_load=DetailsState.load_json_data, title="影视详情")
@template
def details() -> rx.Component:
    return rx.box(
        rx.cond(
            DetailsState.loading,
            rx.center(
                rx.vstack(
                    rx.spinner(color="red", size="3", class_name="animate-spin"),
                    rx.text(
                        "正在加载详情...", class_name="text-gray-600 font-medium mt-3"
                    ),
                    align="center",
                    spacing="3",
                ),
                class_name="py-20",
            ),
            rx.container(
                media_details_component(
                    vod_details=DetailsState.vod_details,
                    on_unmount=DetailsState.unmount_clean,
                ),
                size="4",
                width="95%",
            ),
        ),
        class_name="min-h-[calc(100vh-70px-64px)] bg-gray-50",
    )
