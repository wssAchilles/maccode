from __future__ import annotations

DEFAULT_TEMPORAL_PROMPT = (
    "【时间/条件环境】：当前未绑定特殊时间或天气模板。请按常规道路监控场景解释，"
    "并优先引用 JSON 中已经出现的风险信号。"
)

TEMPORAL_PROMPTS: dict[str, str] = {
    "night": (
        "【时间/条件环境】：当前为深夜或低照度环境。视线变差会放大感知与驾驶反应"
        "风险，请更关注轨迹尾迹偏移、突然加减速和低置信度速度区间。"
    ),
    "late_night": (
        "【时间/条件环境】：当前为凌晨时段。行人与车辆可见性下降，异常轨迹比"
        "单点速度更需要被解释。"
    ),
    "rain": (
        "【时间/条件环境】：当前存在雨天条件。湿滑路面会增加制动距离，并放大"
        "Model 6 误差传播影响。"
    ),
    "waterlogging": (
        "【时间/条件环境】：当前路面存在积水。请对 km/h 绝对值保持谨慎，更关注"
        "ByteTrack trajectory tail 偏离、低速打滑和局部拥堵。"
    ),
    "rush_hour": (
        "【时间/条件环境】：当前接近早晚高峰。请结合交通流状态、人群密度和短时"
        "排队趋势判断是否存在 Traffic Wave。"
    ),
}


def get_prompt(keys: list[str]) -> str:
    blocks = [TEMPORAL_PROMPTS[key] for key in keys if key in TEMPORAL_PROMPTS]
    return "\n".join(dict.fromkeys(blocks)) or DEFAULT_TEMPORAL_PROMPT
