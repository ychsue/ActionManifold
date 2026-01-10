# am_meta/core_mainline.py

from datetime import datetime
from src.am_core.feature.feature_unit import feature_unit
from src.am_core.graph import FeatureUnitGraph


class AMCoreMainline:
    """
    AM-Core 的開發主線語意。
    這裡不實作功能，只用 FeatureUnit 描述「我們要把 AM-Core 變成什麼」。
    """

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="design_main_kickoff",
        display_name="起點",
        status="done",
        notes="定義 AM-Core 開發主線的語意起點",
        scheduled=datetime(2025, 12, 1),
        due=datetime(2025, 12, 15),
    )
    def main_kickoff(self):
        pass

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="design_feature_unit_graph",
        display_name="設計 FeatureUnitGraph",
        status="done",
        depends=[main_kickoff],
        notes="設計 FeatureUnitGraph 的語意與 API",
    )
    def design_feature_unit_graph(self):
        pass

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="implement_feature_unit_graph",
        display_name="實作 FeatureUnitGraph",
        status="done",
        depends=[design_feature_unit_graph, FeatureUnitGraph],
        notes="實作 FeatureUnitGraph 與基本圖操作",
    )
    def implement_feature_unit_graph(self):
        pass

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="design_cli",
        display_name="設計 CLI",
        status="planned",
        depends=[main_kickoff],
        notes="設計 AM CLI 的指令語意（roadmap / mainline / graph / timeline / gantt）",
    )
    def design_cli(self):
        pass

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="implement_cli",
        display_name="實作 CLI",
        status="planned",
        depends=[design_cli],
        notes="實作 CLI 並串接 FeatureUnitGraph / report / visualize",
    )
    def implement_cli(self):
        pass

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="design_meta_self_description",
        display_name="自我描述（Meta）",
        status="planned",
        depends=[implement_feature_unit_graph],
        notes="設計 AM 如何用自己的 FeatureUnit 來描述自己（core + meta）",
    )
    def design_meta_self_description(self):
        pass

    @feature_unit(
        belongs_to=["AMCoreMeta"],
        id="future_interactive_graph",
        display_name="未來互動式語意圖",
        status="imagined",
        depends=[implement_feature_unit_graph],
        notes="未來支援 PyVis / Cytoscape.js 的互動式語意圖",
    )
    def future_interactive_graph(self):
        pass