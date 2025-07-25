import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';

// Correct imports from lavi_specs components
import { LaviLogo } from '../components/ui/LaviLogo';
import { ParticleBackground } from '../components/ui/ParticleBackground';
import { DynamicForm } from '../components/form/DynamicForm';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { BusinessData } from '../types';
import { useAuth } from '../hooks/useAuth';
import { useBusinessData } from '../hooks/useBusinessData';

interface PageParams {
  businessId?: string;
}

export const CorrectPageComponent: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { businessId } = useParams<PageParams>();
  const { user, isAuthenticated } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [businessData, setBusinessData] = useState<BusinessData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load business data when component mounts or businessId changes
  useEffect(() => {
    const loadBusinessData = async () => {
      if (!businessId) {
        setError(t('errors.businessIdRequired'));
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        
        // Using the custom hook for business data
        const data = await useBusinessData(businessId);
        setBusinessData(data);
      } catch (err) {
        console.error('Failed to load business data:', err);
        setError(t('errors.loadingFailed'));
      } finally {
        setIsLoading(false);
      }
    };

    loadBusinessData();
  }, [businessId, t]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated && !isLoading) {
      navigate('/login', { state: { from: `/business/${businessId}` } });
    }
  }, [isAuthenticated, isLoading, navigate, businessId]);

  const handleFormSubmit = async (formData: any) => {
    try {
      console.log('Submitting form data:', formData);
      // Handle form submission
      navigate('/success', { state: { businessId, formData } });
    } catch (error) {
      console.error('Form submission error:', error);
      setError(t('errors.submissionFailed'));
    }
  };

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  // Animation variants for page transitions
  const pageVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ParticleBackground />
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ParticleBackground />
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <h2 className="text-red-600 text-xl font-semibold mb-4">{t('errors.title')}</h2>
          <p className="text-gray-700 mb-6">{error}</p>
          <Link 
            to="/" 
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {t('navigation.backToHome')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen relative">
        <ParticleBackground />
        
        {/* Header */}
        <header className="relative z-10 bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <Link to="/" className="flex items-center space-x-2">
              <LaviLogo size="medium" />
              <span className="text-xl font-semibold">{t('app.name')}</span>
            </Link>
            
            <nav className="flex items-center space-x-6">
              <Link to="/dashboard" className="text-gray-700 hover:text-blue-600">
                {t('navigation.dashboard')}
              </Link>
              <Link to="/profile" className="text-gray-700 hover:text-blue-600">
                {t('navigation.profile')}
              </Link>
              
              {/* Language Selector */}
              <select
                onChange={(e) => handleLanguageChange(e.target.value)}
                value={i18n.language}
                className="border rounded px-2 py-1"
              >
                <option value="en">English</option>
                <option value="es">Español</option>
                <option value="fr">Français</option>
              </select>
              
              {user && (
                <span className="text-sm text-gray-600">
                  {t('user.welcome', { name: user.name })}
                </span>
              )}
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <motion.main
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{ duration: 0.3 }}
          className="relative z-10 container mx-auto px-4 py-8"
        >
          <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold mb-2">
              {t('business.formTitle')}
            </h1>
            <p className="text-gray-600 mb-8">
              {t('business.formDescription', { businessName: businessData?.name })}
            </p>

            {businessData && (
              <div className="bg-white rounded-lg shadow-lg p-8">
                <DynamicForm
                  businessData={businessData}
                  onSubmit={handleFormSubmit}
                  className="space-y-6"
                />
              </div>
            )}
          </div>
        </motion.main>

        {/* Footer */}
        <footer className="relative z-10 bg-gray-100 mt-16">
          <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center">
              <p className="text-gray-600">
                {t('footer.copyright', { year: new Date().getFullYear() })}
              </p>
              <div className="flex space-x-4">
                <Link to="/privacy" className="text-gray-600 hover:text-blue-600">
                  {t('footer.privacy')}
                </Link>
                <Link to="/terms" className="text-gray-600 hover:text-blue-600">
                  {t('footer.terms')}
                </Link>
                <Link to="/contact" className="text-gray-600 hover:text-blue-600">
                  {t('footer.contact')}
                </Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
};

export default CorrectPageComponent;