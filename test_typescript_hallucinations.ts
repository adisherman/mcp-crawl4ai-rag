// Test TypeScript file for hallucination detection
// This tests if our system can detect non-existent components and methods

// Real imports that should exist in lavi_specs
import { DynamicForm } from 'src/components/form/DynamicForm';
import { FormField, BusinessData } from 'src/types';

// Hallucinated imports - these don't exist
import { SuperDynamicForm } from 'src/components/form/SuperDynamicForm';
import { MagicValidator } from 'src/utils/MagicValidator';

// Testing component usage
function testComponentUsage() {
  // REAL: DynamicForm exists
  const form = new DynamicForm();
  
  // HALLUCINATION: SuperDynamicForm doesn't exist
  const superForm = new SuperDynamicForm();
  
  // HALLUCINATION: DynamicForm doesn't have these methods
  form.enableDarkMode();
  form.setMagicValidation(true);
  
  // Testing interface usage
  const field: any = {
    id: 'test',
    type: 'text',
    label: 'Test Field',
    // HALLUCINATION: FormField doesn't have magicRequired property
    magicRequired: true
  };
}

// Testing class that extends real component
// HALLUCINATION: Can't extend DynamicForm like this
class SuperForm extends DynamicForm {
  // HALLUCINATION: Adding non-existent methods
  enableAutoSave() {
    console.log('Auto save enabled');
  }
}

// Using real service but with fake methods
import { EmailService } from 'src/services/emailService';

function testEmailService() {
  const service = new EmailService();
  
  // HALLUCINATION: EmailService doesn't have sendMagicEmail method
  service.sendMagicEmail('test@example.com', 'Magic Subject', 'Magic Body');
  
  // HALLUCINATION: EmailService doesn't have these static methods
  EmailService.configureMagicSettings({
    enableSparkles: true,
    magicLevel: 'maximum'
  });
}

// Testing non-existent types
// HALLUCINATION: These types don't exist in lavi_specs
type MagicFormData = BusinessData & {
  magicProperties: string[];
  enableAutoValidation: boolean;
};

interface SuperFormField extends FormField {
  superValidation?: boolean;
  magicTransform?: (value: any) => any;
}

export { testComponentUsage, SuperForm, testEmailService };