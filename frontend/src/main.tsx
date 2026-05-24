import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import MobileApp from './MobileApp.tsx';
import './index.css';

function isMobileRoute(): boolean {
  if (typeof window === 'undefined') return false;
  const {pathname, search} = window.location;
  if (pathname.startsWith('/m') && (pathname === '/m' || pathname.startsWith('/m/'))) {
    return true;
  }
  if (new URLSearchParams(search).get('mobile') === '1') return true;
  return false;
}

const Root = isMobileRoute() ? MobileApp : App;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
