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
        inference_status: {
          enabled: true,
          ready: true,
          engine: 'cerberus_signal_transformer_lstm',
          mode: 'observe',
          metadata: {
            lookback: 256,
          },
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

    expect(screen.getAllByText(/artifact cache warming/i).length).toBe(2)
    expect(screen.getAllByText(/common\.na/i).length).toBeGreaterThan(0)
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
    expect(screen.getByText(/离线 Macro F1|Offline Macro F1/i)).toBeTruthy()
  })
})
