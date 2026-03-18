from typing import Any, Dict, List

from am_core.interactive.utils import merge_ctx_delta_with_validation, merge_dict_with_validation, regexp_d_get

from ..types import AwaitInput, InteractiveAdapter, ModifiedDecision

class FakeAdapter(InteractiveAdapter):
    """
    Test adapter: applies partial patches to suggested values.
    Useful for simulating any adapter behavior in tests.
    """

    def __init__(
        self,
        output_patch: Dict[str, Dict[str, Any]] | None = None,
        ctx_delta_patch: Dict[str, List[Dict[str, Any]]] | None = None,
        metadata_patch: Dict[str, Dict[str, Any]] | None = None,
    ) -> None:
        self.output_patch = output_patch or {}
        self.ctx_delta_patch = ctx_delta_patch or {}
        self.metadata_patch = metadata_patch or {}

    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        suggested = await_input["suggested"]

        # output
        output = merge_dict_with_validation(
            "output",
            suggested["output"],
            regexp_d_get(self.output_patch, await_input["state"], {}),
        )

        # ctx_delta
        ctx_delta = merge_ctx_delta_with_validation(
            suggested["ctx_delta"],
            regexp_d_get(self.ctx_delta_patch, await_input["state"], []),
        )

        # metadata_delta
        metadata_delta = merge_dict_with_validation(
            "metadata_delta",
            suggested["metadata_delta"],
            regexp_d_get(self.metadata_patch, await_input["state"], {}),
        )

        return ModifiedDecision(
            output=output,
            ctx_delta=ctx_delta,
            metadata_delta=metadata_delta,
        )


