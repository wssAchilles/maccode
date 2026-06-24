import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { envelope, lifecycleRiskQueueFixture } from '../../mocks/fixtures';
import { LifecyclePage } from '../../pages/LifecyclePage';
import { renderWithProviders } from '../render';
import { server } from '../server';

describe('LifecyclePage', () => {
  it('renders lifecycle summary, segments, risk queue, and category affinity', async () => {
    renderWithProviders(<LifecyclePage />);

    expect(await screen.findByText('用户生命周期与价值分层')).toBeInTheDocument();
    expect(await screen.findByText('生命周期契约 v1')).toBeInTheDocument();
    expect(await screen.findByText('536017300')).toBeInTheDocument();
    expect(await screen.findByText('分层覆盖矩阵')).toBeInTheDocument();
    expect(await screen.findByText('每类用户都可见，但只下钻代表样本')).toBeInTheDocument();
    expect((await screen.findAllByText('冠军用户')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('浏览用户')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('高价值')).length).toBeGreaterThan(0);
    expect(await screen.findByText('规则阈值，不是用户数')).toBeInTheDocument();
    expect(await screen.findByText('代表运营队列')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '用户生命周期运营动作队列' })).toBeInTheDocument();
  });

  it('switches lifecycle console views from the segmented controls', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LifecyclePage />);

    await user.click(await screen.findByRole('button', { name: '运营队列' }));
    expect(await screen.findByRole('table', { name: '当前视图代表用户队列' })).toBeInTheDocument();
    expect((await screen.findAllByText('当前视图：运营队列')).length).toBeGreaterThan(0);

    await user.click(screen.getByRole('button', { name: '规则解释' }));
    expect(await screen.findByText('当前视图：规则解释')).toBeInTheDocument();
    expect(await screen.findByText('规则阈值，不是用户数')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '分层矩阵' }));
    expect(await screen.findByText('当前视图：分层矩阵')).toBeInTheDocument();
    expect(await screen.findByLabelText('生命周期分层矩阵')).toBeInTheDocument();
  });

  it('explains when a populated segment is missing from the preview queue', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('/api/v1/lifecycle/risk-queue', () =>
        HttpResponse.json(envelope(lifecycleRiskQueueFixture.filter((row) => row.lifecycle_segment !== 'cart_intent'))),
      ),
    );

    renderWithProviders(<LifecyclePage />);

    await user.click(await screen.findByRole('button', { name: '运营队列' }));
    const cartButtons = await screen.findAllByRole('button', { name: '加购意图' });
    await user.click(cartButtons[cartButtons.length - 1]);

    expect((await screen.findAllByText('加购意图 有全量用户，但预览样本未覆盖')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/加购意图 全量命中 34 人/)).length).toBeGreaterThan(0);
  });
});
