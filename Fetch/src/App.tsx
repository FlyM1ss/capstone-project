import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { UserProvider } from '@/context/UserContext';
import Layout from '@/components/Layout/Layout';
import SearchPage from '@/pages-views/SearchPage/SearchPage';
import ResultsPage from '@/pages-views/ResultsPage/ResultsPage';
import AccountPage from '@/pages-views/AccountPage/AccountPage';
import DocumentPage from '@/pages-views/DocumentPage/DocumentPage';

export default function App() {
  return (
    <BrowserRouter>
      <UserProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/account" element={<AccountPage />} />
          <Route path="/document/:id" element={<DocumentPage />} />
          </Routes>
        </Layout>
      </UserProvider>
    </BrowserRouter>
  );
}
