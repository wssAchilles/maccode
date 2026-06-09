import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AttributionPage } from '../../pages/AttributionPage';
import { renderWithProviders } from '../render';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title }: { title: string }) => <div role="img" aria-label={title} />,
}));

describe('AttributionPage', () => {
  it('renders attribution summary, quality evidence, entity ranking, assists, and paths', async () => {
    renderWithProviders(<AttributionPage />);

    expect(await screen.findByText('营收归因与辅助转化洞察')).toBeInTheDocument();
    expect(await screen.findByText('revenue-attribution/v1')).toBeInTheDocument();
    expect(await screen.findByText(/归因质量需要复核/)).toBeInTheDocument();
    expect((await screen.findAllByText('electronics')).length).toBeGreaterThan(0);
    expect(await screen.findByRole('table', { name: '营收归因实体排行' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '辅助转化机会' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '归因购买路径' })).toBeInTheDocument();
  });

  it('lets operators switch entity type and attribution model', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AttributionPage />);

    await screen.findByLabelText('归因对象');
    await user.selectOptions(screen.getByLabelText('归因模型'), 'linear');
    await user.selectOptions(screen.getByLabelText('归因对象'), 'category');

    expect((await screen.findAllByText('Linear')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('monitor_assist_entity')).length).toBeGreaterThan(0);
  });
});
