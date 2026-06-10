import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { CommandPalette } from '../../components/layout/CommandPalette';
import { renderWithProviders } from '../render';

describe('CommandPalette', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('opens, filters destinations, and keeps navigation searchable', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CommandPalette />);

    await user.click(screen.getByRole('button', { name: '打开命令面板' }));
    const input = screen.getByRole('combobox', { name: '搜索页面、指标或工作流' });
    expect(input).toHaveAttribute('aria-expanded', 'true');

    await user.type(input, '用户');

    expect(await screen.findByRole('option', { name: /用户分层/ })).toBeInTheDocument();
    expect(screen.queryByText('明细查询')).not.toBeInTheDocument();
  });

  it('supports keyboard search and enter navigation', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CommandPalette />);

    await user.keyboard('{Control>}k{/Control}');
    const input = screen.getByRole('combobox', { name: '搜索页面、指标或工作流' });

    expect(input).toHaveFocus();

    await user.type(input, '特征');
    await user.keyboard('{Enter}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('restores focus to the trigger after escape closes the dialog', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CommandPalette />);
    const trigger = screen.getByRole('button', { name: '打开命令面板' });

    await user.click(trigger);
    await user.keyboard('{Escape}');

    expect(trigger).toHaveFocus();
  });
});
