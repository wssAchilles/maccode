import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../render';
import { OptimizationPage } from '../../pages/OptimizationPage';

describe('OptimizationPage', () => {
  it('renders solver status and plan rows', async () => {
    renderWithProviders(<OptimizationPage />);

    expect(await screen.findByText('促销预算与推荐位优化')).toBeInTheDocument();
    expect(await screen.findByText('optimal')).toBeInTheDocument();
    expect(await screen.findAllByText('feature_slot')).toHaveLength(2);
    expect(await screen.findByText('1004856')).toBeInTheDocument();
  });
});
