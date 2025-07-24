// Test file to validate TypeScript hallucination detection
// This file intentionally contains both valid and hallucinated code

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

// These would be valid imports from lavi_specs (not using actual paths to avoid resolution issues)
// import { DynamicForm } from 'lavi_specs/components/form/DynamicForm';
// import { FormField, BusinessData } from 'lavi_specs/types';
// import { FormInput } from 'lavi_specs/components/form';

// HALLUCINATED: These components/functions don't exist in lavi_specs
// import { SuperForm } from 'lavi_specs/components/form/SuperForm';
// import { validateBusinessData } from 'lavi_specs/utils/businessValidator';
// import { MagicFormWrapper } from 'lavi_specs/components/ui/MagicFormWrapper';

// Simulating usage of real interfaces from lavi_specs
interface TestComponentProps {
  data: any; // Would be BusinessData
  onComplete: (result: any) => void;
  enableMagicMode?: boolean; // HALLUCINATION: This prop pattern doesn't exist
}

const TestLaviComponent: React.FC<TestComponentProps> = ({ data, onComplete, enableMagicMode }) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // HALLUCINATION: validateBusinessData doesn't exist in lavi_specs
    // const isValid = validateBusinessData(data);
    console.log('Component mounted');
  }, [data]);

  const handleSubmit = async (values: any) => {
    setIsLoading(true);
    try {
      // HALLUCINATION: DynamicForm.validateAsync doesn't exist
      // await DynamicForm.validateAsync(values);
      
      // HALLUCINATION: BusinessData doesn't have a process method
      // const result = await data.process();
      
      onComplete(values);
    } catch (error) {
      console.error('Submission failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="test-component">
      <h1>{t('test.title')}</h1>
      
      {/* Would use real components here */}
      {/* <DynamicForm businessData={data} onSubmit={handleSubmit} /> */}
      
      {/* HALLUCINATION: SuperForm doesn't exist */}
      {/* <SuperForm data={data} autoSave={true} validationMode="aggressive" /> */}
      
      {/* HALLUCINATION: FormInput doesn't have these props */}
      {/* <FormInput 
        name="test"
        label="Test"
        enableAutoComplete={true}
        validationStrategy="realtime"
        onMagicChange={(value) => console.log(value)}
      /> */}
      
      <button onClick={() => handleSubmit({})}>Submit</button>
    </div>
  );
};

// Creating fake usage patterns that would be hallucinations
class NonExistentEmailService {
  static async sendMagicEmail(to: string, subject: string): Promise<void> {
    // EmailService exists in lavi_specs but doesn't have sendMagicEmail method
  }
}

// HALLUCINATION: This interface doesn't exist in lavi_specs types
interface MagicFormField extends FormField {
  magicValidation?: boolean;
  autoCompleteStrategy?: string;
}

// Using a real component name but with wrong props/methods
const fakeUsage = () => {
  // DynamicForm exists but these are hallucinated usages:
  // DynamicForm.setGlobalTheme('dark');
  // DynamicForm.enableMagicMode();
  
  // Real interface but fake properties:
  const field: MagicFormField = {
    id: 'test',
    type: 'magic', // HALLUCINATION: 'magic' is not a valid type
    label: 'Test',
    magicValidation: true, // HALLUCINATION: This property doesn't exist
  };
};

export default TestLaviComponent;