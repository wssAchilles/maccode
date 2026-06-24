import { Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { ChartFilterProvider } from '../context/ChartFilterContext';
import { AffinityPage } from '../pages/AffinityPage';
import { AnomalyPage } from '../pages/AnomalyPage';
import { AttributionPage } from '../pages/AttributionPage';
import { BehaviorPage } from '../pages/BehaviorPage';
import { CartRecoveryPage } from '../pages/CartRecoveryPage';
import { ConversionPage } from '../pages/ConversionPage';
import { CohortsPage } from '../pages/CohortsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { ExperimentsPage } from '../pages/ExperimentsPage';
import { FeatureMartPage } from '../pages/FeatureMartPage';
import { ForecastingPage } from '../pages/ForecastingPage';
import { JourneyPage } from '../pages/JourneyPage';
import { LifecyclePage } from '../pages/LifecyclePage';
import { LiveTrainingPage } from '../pages/LiveTrainingPage';
import { OpsPage } from '../pages/OpsPage';
import { OptimizationPage } from '../pages/OptimizationPage';
import { PortfolioPage } from '../pages/PortfolioPage';
import { QualityPage } from '../pages/QualityPage';
import { ControlledQueryPage } from '../pages/ControlledQueryPage';
import { RankingsPage } from '../pages/RankingsPage';
import { RecommendationsPage } from '../pages/RecommendationsPage';
import { TablePage } from '../pages/TablePage';

export const appRoutes = [
  { index: true, path: '/', element: <DashboardPage /> },
  { path: '/behavior', element: <BehaviorPage /> },
  { path: '/conversion', element: <ConversionPage /> },
  { path: '/cart-recovery', element: <CartRecoveryPage /> },
  { path: '/attribution', element: <AttributionPage /> },
  { path: '/journey', element: <JourneyPage /> },
  { path: '/optimization', element: <OptimizationPage /> },
  { path: '/query', element: <ControlledQueryPage /> },
  { path: '/recommendations', element: <RecommendationsPage /> },
  { path: '/anomalies', element: <AnomalyPage /> },
  { path: '/lifecycle', element: <LifecyclePage /> },
  { path: '/cohorts', element: <CohortsPage /> },
  { path: '/portfolio', element: <PortfolioPage /> },
  { path: '/experiments', element: <ExperimentsPage /> },
  { path: '/forecasting', element: <ForecastingPage /> },
  { path: '/live-training', element: <LiveTrainingPage /> },
  { path: '/affinity', element: <AffinityPage /> },
  { path: '/feature-mart', element: <FeatureMartPage /> },
  { path: '/quality', element: <QualityPage /> },
  { path: '/rankings', element: <RankingsPage /> },
  { path: '/table', element: <TablePage /> },
  { path: '/ops', element: <OpsPage /> },
];

export function AppRoutes() {
  return (
    <ChartFilterProvider>
    <Routes>
      <Route element={<AppShell />}>
        {appRoutes.map((route) =>
          route.index ? (
            <Route index element={route.element} key={route.path} />
          ) : (
            <Route path={route.path.slice(1)} element={route.element} key={route.path} />
          ),
        )}
      </Route>
    </Routes>
    </ChartFilterProvider>
  );
}
