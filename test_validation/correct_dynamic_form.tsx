import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import * as z from 'zod';

// Correct imports from lavi_specs
import { DynamicForm } from '../components/form/DynamicForm';
import { BusinessData, FormField, FormSection, ValidationRule } from '../types';
import { formHelpers } from '../utils/formHelpers';

// Define proper validation schema for dynamic form
const createDynamicSchema = (fields: FormField[]) => {
  const schemaObject: Record<string, z.ZodTypeAny> = {};
  
  fields.forEach(field => {
    let fieldSchema: z.ZodTypeAny = z.string();
    
    if (field.type === 'number') {
      fieldSchema = z.number();
    } else if (field.type === 'email') {
      fieldSchema = z.string().email('Invalid email format');
    } else if (field.type === 'date') {
      fieldSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date format');
    }
    
    if (field.required) {
      if (field.type === 'number') {
        fieldSchema = fieldSchema.refine(val => val !== undefined && val !== null, {
          message: `${field.label} is required`
        });
      } else {
        fieldSchema = z.string().min(1, `${field.label} is required`);
      }
    } else {
      fieldSchema = fieldSchema.optional();
    }
    
    schemaObject[field.id] = fieldSchema;
  });
  
  return z.object(schemaObject);
};

interface CorrectDynamicFormProps {
  businessData: BusinessData;
  onComplete: (data: any) => Promise<void>;
}

export const CorrectDynamicForm: React.FC<CorrectDynamicFormProps> = ({ 
  businessData, 
  onComplete 
}) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Create dynamic form sections based on business data
  const formSections: FormSection[] = businessData.sections || [
    {
      id: 'contact-info',
      title: t('form.sections.contactInfo'),
      fields: [
        {
          id: 'fullName',
          type: 'text',
          label: t('form.fields.fullName'),
          required: true,
          placeholder: t('form.placeholders.fullName')
        },
        {
          id: 'email',
          type: 'email',
          label: t('form.fields.email'),
          required: true,
          placeholder: t('form.placeholders.email')
        },
        {
          id: 'phone',
          type: 'tel',
          label: t('form.fields.phone'),
          required: false,
          placeholder: t('form.placeholders.phone'),
          validation: {
            pattern: /^[\d\s\-\+\(\)]+$/,
            message: t('form.validation.invalidPhone')
          }
        }
      ]
    },
    {
      id: 'business-details',
      title: t('form.sections.businessDetails'),
      fields: [
        {
          id: 'companyName',
          type: 'text',
          label: t('form.fields.companyName'),
          required: true
        },
        {
          id: 'industry',
          type: 'select',
          label: t('form.fields.industry'),
          required: true,
          options: [
            { value: 'tech', label: t('form.options.technology') },
            { value: 'finance', label: t('form.options.finance') },
            { value: 'healthcare', label: t('form.options.healthcare') },
            { value: 'retail', label: t('form.options.retail') },
            { value: 'other', label: t('form.options.other') }
          ]
        },
        {
          id: 'employees',
          type: 'number',
          label: t('form.fields.numberOfEmployees'),
          required: false,
          min: 1,
          max: 10000
        }
      ]
    }
  ];

  // Collect all fields for schema generation
  const allFields = formSections.flatMap(section => section.fields);
  const validationSchema = createDynamicSchema(allFields);

  const handleSubmit = useCallback(async (formData: any) => {
    setIsLoading(true);
    setValidationErrors({});

    try {
      // Validate with zod
      const validatedData = validationSchema.parse(formData);
      
      // Use form helpers for additional processing
      const processedData = formHelpers.processFormData(validatedData);
      
      // Call completion handler
      await onComplete(processedData);
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors: Record<string, string> = {};
        error.errors.forEach(err => {
          if (err.path[0]) {
            errors[err.path[0].toString()] = err.message;
          }
        });
        setValidationErrors(errors);
      } else {
        console.error('Form submission error:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [validationSchema, onComplete]);

  const handleFieldChange = useCallback((fieldId: string, value: any) => {
    // Clear validation error for this field when it changes
    if (validationErrors[fieldId]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldId];
        return newErrors;
      });
    }
  }, [validationErrors]);

  return (
    <div className="dynamic-form-container">
      <DynamicForm
        businessData={businessData}
        sections={formSections}
        onSubmit={handleSubmit}
        onFieldChange={handleFieldChange}
        validationErrors={validationErrors}
        isLoading={isLoading}
        submitButtonText={t('form.submit')}
        className="max-w-2xl mx-auto"
      />
    </div>
  );
};

// Example of how to use the component with custom validation rules
export const ExampleUsage: React.FC = () => {
  const { t } = useTranslation();
  
  const customBusinessData: BusinessData = {
    id: 'custom-form',
    type: 'registration',
    sections: [
      {
        id: 'account-setup',
        title: 'Account Setup',
        fields: [
          {
            id: 'username',
            type: 'text',
            label: 'Username',
            required: true,
            minLength: 3,
            maxLength: 20,
            validation: {
              pattern: /^[a-zA-Z0-9_]+$/,
              message: 'Username can only contain letters, numbers, and underscores'
            }
          },
          {
            id: 'password',
            type: 'password',
            label: 'Password',
            required: true,
            minLength: 8,
            validation: {
              pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
              message: 'Password must contain uppercase, lowercase, and numbers'
            }
          }
        ]
      }
    ]
  };

  const handleFormComplete = async (data: any) => {
    console.log('Form completed with data:', data);
    // Perform API call or other actions
  };

  return (
    <CorrectDynamicForm
      businessData={customBusinessData}
      onComplete={handleFormComplete}
    />
  );
};

export default CorrectDynamicForm;