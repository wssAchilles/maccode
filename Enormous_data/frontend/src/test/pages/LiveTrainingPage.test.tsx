import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { LiveTrainingPage } from '../../pages/LiveTrainingPage';
import { renderWithProviders } from '../render';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title, subtitle }: { title: string; subtitle: string }) => (
    <section aria-label={title}>
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </section>
  ),
}));

describe('LiveTrainingPage', () => {
  it('renders weather signal, training status, metric comparison, and impact evidence', async () => {
    renderWithProviders(<LiveTrainingPage />);

    expect(await screen.findByText('实时训练与天气影响')).toBeInTheDocument();
    expect(await screen.findByText(/历史天气只进入 2019 训练\/回测/)).toBeInTheDocument();
    expect(await screen.findByRole('list', { name: '实时训练证据链' })).toBeInTheDocument();
    expect(await screen.findByText('实时获取数据')).toBeInTheDocument();
    expect(await screen.findByText('特征融合')).toBeInTheDocument();
    expect(await screen.findByText('微批训练/回测')).toBeInTheDocument();
    expect(await screen.findByText('实时推理')).toBeInTheDocument();
    expect(await screen.findByText('实时渲染')).toBeInTheDocument();
    expect(await screen.findByLabelText('时间穿越隔离证明')).toBeInTheDocument();
    expect((await screen.findAllByText('28.4°C')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('100.0%')).length).toBeGreaterThan(0);
    expect(await screen.findByText('数据血缘')).toBeInTheDocument();
    expect(await screen.findByText('Baseline vs Weather-enhanced')).toBeInTheDocument();
    expect(await screen.findByText('实时业务影响评分')).toBeInTheDocument();
    expect(await screen.findByText('未来 24 小时影响曲线')).toBeInTheDocument();
    expect(await screen.findByText('未来 24h forecast impact')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '未来24小时影响清单' })).toBeInTheDocument();
    expect(await screen.findByText('仅实时推理')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '天气影响清单' })).toBeInTheDocument();
  });

  it('starts a live training refresh from the command button', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LiveTrainingPage />);

    await user.click(await screen.findByRole('button', { name: '刷新实时训练' }));

    expect(await screen.findByText('实时训练与天气影响')).toBeInTheDocument();
  });
});
