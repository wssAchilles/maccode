from __future__ import annotations

DEFAULT_SPATIAL_PROMPT = (
    "【空间环境】：当前监控区域未绑定特殊空间模板。请仅根据 dynamic_context.scene、"
    "risk_signals 与 FrameReport JSON 进行保守推理。"
)

SPATIAL_PROMPTS: dict[str, str] = {
    "school_zone": (
        "【空间环境】：当前监控区域为学校门口。对行人的安全阈值要求极高，重点关注"
        "斑马线上的行人、校门口聚集人群，以及任何车速大于 **30 km/h** 的行为。"
        "此区域启用 Model 9 Crowd 密度模型时，应将 crowds 二维黎曼积分人数作为"
        "高优先级安全信号。"
    ),
    "school": (
        "【空间环境】：当前区域具备学校周边属性。请将儿童、斑马线和低速通行安全"
        "作为优先判断维度。"
    ),
    "hospital_gate": (
        "【空间环境】：当前监控区域为医院入口。救护车、行人密集、临停车辆与急诊"
        "通道占用会显著放大安全风险；Crowd 密度和道路阻塞需要优先解释。"
    ),
    "hospital": (
        "【空间环境】：当前区域具备医院周边属性。请关注人车混行、急救通道、行动"
        "不便人群和短时拥堵的联动风险。"
    ),
    "intersection": (
        "【空间环境】：当前监控区域为城市十字路口。请综合信号灯状态、停止线、"
        "车速、轨迹方向和人群穿越行为进行风险研判。"
    ),
    "crosswalk": (
        "【空间环境】：当前区域包含斑马线或行人过街路径。请优先关注车辆速度与"
        "行人轨迹的冲突风险。"
    ),
}


def get_prompt(keys: list[str]) -> str:
    blocks = [SPATIAL_PROMPTS[key] for key in keys if key in SPATIAL_PROMPTS]
    return "\n".join(dict.fromkeys(blocks)) or DEFAULT_SPATIAL_PROMPT
