import { Routes, Route } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import HomePage from '../pages/HomePage'
import ExhibitsPage from '../pages/ExhibitsPage'
import ExhibitDetailPage from '../pages/ExhibitDetailPage'
import MapPage from '../pages/MapPage'
import ChatPage from '../pages/ChatPage'
import SettingsPage from '../pages/SettingsPage'
import TourPage from '../pages/TourPage'
import TourRunPage from '../pages/TourRunPage'
import NavigationPage from '../pages/NavigationPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="exhibits" element={<ExhibitsPage />} />
        <Route path="exhibits/:id" element={<ExhibitDetailPage />} />
        <Route path="map" element={<MapPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="tour" element={<TourPage />} />
        <Route path="tour/run" element={<TourRunPage />} />
        <Route path="navigate" element={<NavigationPage />} />
      </Route>
    </Routes>
  )
}
