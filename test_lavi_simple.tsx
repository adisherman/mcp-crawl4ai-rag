import React from 'react';
import { DynamicForm } from './components/form/DynamicForm';
import { SuperForm } from './components/form/SuperForm'; // HALLUCINATION
import { FormField, BusinessData } from './types';
import { EmailService } from './services/emailService';

interface TestProps {
  data: BusinessData;
}

const TestComponent: React.FC<TestProps> = ({ data }) => {
  // HALLUCINATION: DynamicForm doesn't have a static validate method
  const isValid = DynamicForm.validate(data);
  
  // HALLUCINATION: EmailService doesn't have sendMagicEmail method
  const sendEmail = () => {
    EmailService.sendMagicEmail('test@test.com', 'Hello');
  };
  
  // Real component usage
  return (
    <DynamicForm 
      businessData={data}
      onSubmit={async (values) => console.log(values)}
    />
  );
};

// HALLUCINATION: This interface doesn't exist
interface MagicFormField extends FormField {
  enableMagic: boolean;
}

export default TestComponent;