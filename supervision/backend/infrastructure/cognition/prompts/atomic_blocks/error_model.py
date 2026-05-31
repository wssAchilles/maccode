from __future__ import annotations

DEFAULT_ERROR_MODEL_PROMPT = (
    "【数学误差模型】：必须引用 Model 6 置信区间、speed_uncertainty_kmh、"
    "speed_confidence 或 calibration_diagnostics 中已有字段；没有字段时只能说明证据不足。"
)

ERROR_MODEL_PROMPTS: dict[str, str] = {
    "uncertainty": DEFAULT_ERROR_MODEL_PROMPT,
    "rain": (
        "【数学误差模型】：雨天会提高观测噪声与制动风险。解释速度时必须同步查看"
        "Model 6 置信区间，避免只凭单点 km/h 结论过度执法。"
    ),
    "waterlogging": (
        "【数学误差模型】：积水条件下误差传播和轨迹偏移概率上升。请同时评估"
        "speed_confidence_interval_kmh、window_residual_m 与 calibration_quality。"
    ),
    "low_confidence": (
        "【数学误差模型】：存在低置信或标定降级信号时，必须将输出表述为风险预警"
        "或复核建议，不得写成确定性处罚结论。"
    ),
}


def get_prompt(keys: list[str]) -> str:
    blocks = [ERROR_MODEL_PROMPTS[key] for key in keys if key in ERROR_MODEL_PROMPTS]
    return "\n".join(dict.fromkeys(blocks)) or DEFAULT_ERROR_MODEL_PROMPT
