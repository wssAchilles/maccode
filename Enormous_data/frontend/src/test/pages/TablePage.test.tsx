import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../render';
import { TablePage } from '../../pages/TablePage';

describe('TablePage', () => {
  it('filters event type and resets to page one', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TablePage />);

    await screen.findByText('electronics.smartphone');
    await user.click(screen.getByRole('button', { name: '下一页' }));
    expect(screen.getByText('第 2 页')).toBeInTheDocument();

    await user.selectOptions(screen.getByRole('combobox', { name: '行为类型' }), 'purchase');

    await waitFor(() => expect(screen.getByText('第 1 页')).toBeInTheDocument());
    expect(await screen.findByText('apparel.shoes')).toBeInTheDocument();
  });

  it('changes page size and opens row inspection', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TablePage />);

    await screen.findByText('electronics.smartphone');
    await user.selectOptions(screen.getByRole('combobox', { name: '每页行数' }), '25');
    await user.click(screen.getAllByRole('button', { name: '查看' })[0]);

    expect(await screen.findByLabelText('选中行为摘要')).toHaveTextContent('商品 1002');
  });
});
