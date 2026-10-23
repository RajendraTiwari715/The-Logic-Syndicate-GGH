import { useState, useEffect } from 'react';
import { AppProvider, useApp } from './store';
import Login from './pages/Login';
import Layout, { type PageId } from './components/Layout';
import Overview from './pages/Overview';
import LiveSurveillance from './pages/LiveSurveillance';
import Cameras from './pages/Cameras';
import Events from './pages/Events';
import ANPR from './pages/ANPR';
import Tracking from './pages/Tracking';
import VirtualFences from './pages/VirtualFences';
import FaceDetection from './pages/FaceDetection';
import GlobalAlarm from './components/GlobalAlarm';
import SuspiciousActivity from './pages/SuspiciousActivity';
import PeopleDetected from './pages/PeopleDetected';
import CameraHealth from './pages/CameraHealth';
import VehicleDetection from './pages/VehicleDetection';
import IntrusionLogs from './pages/IntrusionLogs';
import BlockchainLedger from './pages/BlockchainLedger';

function AppContent() {
  const { user, setSelectedLiveCameraIds } = useApp();
  // Default to overview for the operator console
  const [page, setPage] = useState<PageId>('overview');

  useEffect(() => {
    if (user) {
      setPage('overview');
    }
  }, [user]);

  // Deep linking receiver
  useEffect(() => {
    const handleNav = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail) {
        if (customEvent.detail.page) {
          setPage(customEvent.detail.page as PageId);
        }
        if (customEvent.detail.cameraIds) {
          setSelectedLiveCameraIds(customEvent.detail.cameraIds);
        } else if (customEvent.detail.cameraId) {
          setSelectedLiveCameraIds([customEvent.detail.cameraId]);
        }
      }
    };
    window.addEventListener('appNavigate', handleNav);
    return () => window.removeEventListener('appNavigate', handleNav);
  }, [setSelectedLiveCameraIds]);

  if (!user) return <Login />;

  const renderPage = () => {
    switch (page) {
      case 'overview': 
        return <Overview onNavigate={setPage} />;
      case 'live': return <LiveSurveillance />;
      case 'cameras': return <Cameras />;
      case 'events': return <Events />;
      case 'anpr': return <ANPR />;
      case 'tracking': return <Tracking />;
      case 'fences': return <VirtualFences />;
      case 'faces': return <FaceDetection />;
      case 'suspicious': return <SuspiciousActivity />;
      case 'people': return <PeopleDetected />;
      case 'camera_health': return <CameraHealth />;
      case 'vehicles': return <VehicleDetection />;
      case 'intrusions': return <IntrusionLogs />;
      case 'blockchain': return <BlockchainLedger />;
      default: return <Overview onNavigate={setPage} />;
    }
  };

  return (
    <>
      <GlobalAlarm />
      <Layout current={page} onNavigate={setPage}>
        {renderPage()}
      </Layout>
    </>
  );
}

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
