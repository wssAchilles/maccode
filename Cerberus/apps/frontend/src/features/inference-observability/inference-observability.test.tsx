import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { HealthWorkspace } from '../health/HealthWorkspace'
import { OverviewWorkspace } from '../overview/OverviewWorkspace'
import { InferenceDiagnosticsPanel } from './components/InferenceDiagnosticsPanel'
import { InferenceStatusCard } from './components/InferenceStatusCard'
import { buildInferenceDiagnosticsModel, buildInferenceStatusCardModel } from './view-models'

function renderWithI18n(ui: ReactNode) {
  return render(<I18nProvider>{ui}</I18nProvider>)
}

describe('inference observability module', () => {
  beforeEach(() => {
    useCerberusStore.setState((state) => ({
      ...state,
      strategySummary: {
        ...state.strategySummary,
        inference_catalog: {
          count: 2,
          active_model: {
            model_id: 'cerberus-transformer-lstm',
            version: 'v1',
            source: 'gcs',
            task: 'signal_inference',
            symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            metadata: {
              best_macro_f1: 0.5001,
              lookback: 256,
              horizon: 32,
            },
          },
          models: [
            {
              model_id: 'cerberus-transformer-lstm',
              version: 'v1',
              source: 'gcs',
              task: 'signal_inference',
              symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
              metadata: {
                best_macro_f1: 0.5001,
                lookback: 256,
                horizon: 32,
              },
            },
            {
              model_id: 'cerberus-transformer-lstm',
              version: 'v2',
              source: 'gcs',
              task: 'signal_inference',
              symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
              metadata: {
                best_macro_f1: 0.621,
                lookback: 256,
                horizon: 32,
              },
            },
          ],
        },
        inference_status: {
          enabled: true,
          ready: true,
          engine: 'cerberus_signal_transformer_lstm',
          mode: 'observe',
          metadata: {
            lookback: 256,
          },
          rollout: {
            configured_mode: 'primary',
            target_mode: 'primary',
            effective_mode: 'observe',
            override_active: false,
            auto_promote_enabled: true,
            force_primary: false,
            promotion_eligible: false,
            state_backend: 'redis',
            state_restored: true,
            last_persisted_at: '2026-03-30T00:06:00Z',
            blockers: ['offline_macro_f1_below_threshold'],
            required_observe_ticks: 500,
            compared_ticks: 18,
            required_agreement_ratio: 0.55,
            agreement_ratio: 0.5,
            required_macro_f1: 0.58,
            current_macro_f1: 0.5001,
            started_at: '2026-03-30T00:00:00Z',
            last_transition_at: '2026-03-30T00:00:00Z',
          },
          comparison: {
            observed_ticks: 20,
            compared_ticks: 18,
            agreement_count: 9,
            divergence_count: 9,
            agreement_ratio: 0.5,
            rule_signal_counts: { BUY: 9 },
            inference_signal_counts: { SELL: 9 },
            symbols: [
              {
                symbol: 'BTCUSDT',
                compared_ticks: 12,
                agreement_count: 7,
                divergence_count: 5,
                agreement_ratio: 7 / 12,
              },
            ],
          },
          audit: [
            {
              event_type: 'rollout_holdback',
              created_at: '2026-03-30T00:00:00Z',
              message: 'primary rollout held back until promotion gates pass',
              metadata: {},
            },
            {
              event_type: 'comparison_milestone',
              created_at: '2026-03-30T00:05:00Z',
              message: 'inference comparison reached 10 compared ticks',
              metadata: { milestone: 10 },
            },
            {
              event_type: 'rollout_resumed',
              created_at: '2026-03-30T00:06:00Z',
              message: 'inference rollout state restored from persistent storage',
              metadata: { backend: 'redis' },
            },
          ],
          active_model: {
            model_id: 'cerberus-transformer-lstm',
            version: 'v1',
            source: 'gcs',
            task: 'signal_inference',
            symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            metadata: {
              best_macro_f1: 0.5001,
              lookback: 256,
              horizon: 32,
            },
          },
        },
      },
    }))
  })

  it('renders a compact overview card with model status and CTA', async () => {
    const onOpenHealth = vi.fn()
    const model = buildInferenceStatusCardModel({
      t: (key) => key,
      inferenceStatus: useCerberusStore.getState().strategySummary.inference_status,
    })

    renderWithI18n(<InferenceStatusCard model={model} onOpenHealth={onOpenHealth} />)

    expect(screen.getByText(/cerberus-transformer-lstm/i)).toBeTruthy()
    expect(screen.getByText(/observe/i)).toBeTruthy()
    expect(screen.getByText(/50.0%/i)).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: /查看健康详情|open health details/i }))
    expect(onOpenHealth).toHaveBeenCalledOnce()
  })

  it('renders degraded diagnostics without placeholder noise when metadata is missing', () => {
    const model = buildInferenceDiagnosticsModel({
      t: (key) => key,
      inferenceStatus: {
        enabled: true,
        ready: false,
        engine: 'cerberus_signal_transformer_lstm',
        mode: 'observe',
        reason: 'artifact cache warming',
        metadata: {},
        rollout: {
          configured_mode: 'primary',
          target_mode: 'primary',
          effective_mode: 'observe',
          override_active: false,
          auto_promote_enabled: true,
          force_primary: false,
          promotion_eligible: false,
          state_backend: 'redis',
          state_restored: false,
          last_persisted_at: '',
          blockers: ['agreement_ratio_unavailable'],
          required_observe_ticks: 500,
          compared_ticks: 0,
          required_agreement_ratio: 0.55,
          agreement_ratio: null,
          required_macro_f1: 0.58,
          current_macro_f1: null,
          started_at: '2026-03-30T00:00:00Z',
          last_transition_at: '2026-03-30T00:00:00Z',
        },
        comparison: {
          observed_ticks: 0,
          compared_ticks: 0,
          agreement_count: 0,
          divergence_count: 0,
          agreement_ratio: null,
          rule_signal_counts: {},
          inference_signal_counts: {},
          symbols: [],
        },
        audit: [],
        active_model: {
          model_id: 'cerberus-transformer-lstm',
          version: 'v1',
          source: 'gcs',
          task: 'signal_inference',
          symbols: [],
          metadata: {},
        },
      },
    })

    renderWithI18n(<InferenceDiagnosticsPanel model={model} />)

    expect(screen.getAllByText(/workspace\.inference\.blocker\.agreementUnavailable/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/common\.na/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/workspace\.inference\.stateBackend/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/No symbol-level comparison data yet|暂无标的级对照数据/i)).toBeTruthy()
  })

  it('integrates into overview workspace without replacing existing sections', () => {
    const onSelectWorkspace = vi.fn()

    renderWithI18n(<OverviewWorkspace onSelectWorkspace={onSelectWorkspace} />)

    expect(screen.getAllByText(/推理可观测|Inference observability/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/最近信号|Recent Signals/i)).toBeTruthy()
  })

  it('integrates into health workspace with a read-only diagnostics section', () => {
    renderWithI18n(<HealthWorkspace />)

    expect(screen.getByText(/推理可观测|Inference observability/i)).toBeTruthy()
    expect(screen.getAllByText(/离线 Macro F1|Offline Macro F1/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/推广状态|Promotion state/i)).toBeTruthy()
    expect(screen.getAllByText(/状态后端|State backend/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/标的级对照|Symbol-level comparison/i)).toBeTruthy()
    expect(screen.getByText(/审计时间线|Audit timeline/i)).toBeTruthy()
    expect(screen.getByText(/受控操作|Controlled operations/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /申请晋升为 Primary|Request primary promotion/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /回退到 Observe|Rollback to observe/i })).toBeTruthy()
  })
})
