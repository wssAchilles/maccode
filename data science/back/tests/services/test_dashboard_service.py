import pytest

from services.dashboard_service import DashboardService


@pytest.mark.unit
def test_overview_focus_action_uses_explicit_duty_label_for_model_focus():
    focus_chain = {
        'key': 'model',
        'label': '模型资产',
        'action_label': '打开 AI Lab',
        'workspace_target': 'ai_runtime',
        'card_target': 'runtime_product',
        'incident_target': 'runtime',
        'workspace_brief': 'AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
    }

    action = DashboardService._overview_focus_action(focus_chain)

    assert action['label'] == '开始模型训练'
    assert action['workspace_target'] == 'ai_runtime'
    assert action['card_target'] == 'runtime_product'


@pytest.mark.unit
def test_overview_focus_action_falls_back_for_unknown_chain():
    focus_chain = {
        'key': 'custom',
        'label': '自定义链路',
        'action_label': '打开工作台',
        'workspace_target': 'workspace',
        'card_target': 'summary',
        'incident_target': 'focus',
        'workspace_brief': '自定义工作台。',
    }

    action = DashboardService._overview_focus_action(focus_chain)

    assert action['label'] == '打开工作台'
    assert action['workspace_target_label'] == '工作台'
    assert action['card_target_label'] == '当前卡片'
