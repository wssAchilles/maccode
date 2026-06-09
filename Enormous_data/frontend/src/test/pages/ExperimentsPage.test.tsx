import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ExperimentsPage } from '../../pages/ExperimentsPage';
import { renderWithProviders } from '../render';

describe('ExperimentsPage', () => {
  it('renders experimentation summary, catalog, guardrails, and assignments', async () => {
    renderWithProviders(<ExperimentsPage />);

    expect(await screen.findByText('策略实验与效果评估')).toBeInTheDocument();
    expect(await screen.findByText('growth-experimentation/v1')).toBeInTheDocument();
    expect(await screen.findByText('生命周期再激活策略')).toBeInTheDocument();
    expect(await screen.findByText('min_assignment_users')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '实验分层均衡' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '实验分流样本' })).toBeInTheDocument();
    expect(await screen.findByText('558295000')).toBeInTheDocument();
  });
});
