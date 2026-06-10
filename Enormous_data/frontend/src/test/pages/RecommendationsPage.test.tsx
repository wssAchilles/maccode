import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../render';
import { RecommendationsPage } from '../../pages/RecommendationsPage';

describe('RecommendationsPage', () => {
  it('renders recommendation guardrail metrics and snapshot rows', async () => {
    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('准实时推荐与监控守护')).toBeInTheDocument();
    expect(await screen.findByText(/nearline-recommendation\/v1/)).toBeInTheDocument();
    expect(await screen.findByText('风险原因')).toBeInTheDocument();
    expect(await screen.findByText('freshness')).toBeInTheDocument();
    expect(await screen.findByText('1004856')).toBeInTheDocument();
    expect(await screen.findByText('personalized_category')).toBeInTheDocument();
    expect(await screen.findByText('promotion gate')).toBeInTheDocument();
    expect(await screen.findByLabelText('推荐快照滚动区域')).toHaveClass('panel-scroll');
  });
});
