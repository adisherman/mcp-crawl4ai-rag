import { 
  FormField, 
  BusinessData, 
  ValidationResult,
  TranslatedData,
  ProcessedFormData
} from '../types';

// Correct imports from lavi_specs utilities
import { formHelpers } from '../utils/formHelpers';
import { businessDataTranslator } from '../utils/businessDataTranslator';
import { validationHelpers } from '../utils/validationHelpers';
import { dataProcessor } from '../utils/dataProcessor';

// Example of correct utility usage
export class CorrectUtilityUsage {
  
  // Using formHelpers correctly
  static processFormSubmission(formData: Record<string, any>): ProcessedFormData {
    // Validate form data
    const validationResult = formHelpers.validateFormData(formData);
    
    if (!validationResult.isValid) {
      throw new Error(`Validation failed: ${validationResult.errors.join(', ')}`);
    }
    
    // Clean and normalize the data
    const cleanedData = formHelpers.cleanFormData(formData);
    
    // Process special fields
    const processedData = formHelpers.processSpecialFields(cleanedData);
    
    // Add metadata
    return formHelpers.addFormMetadata(processedData, {
      submittedAt: new Date().toISOString(),
      version: '1.0'
    });
  }
  
  // Using businessDataTranslator correctly
  static translateBusinessData(
    data: BusinessData, 
    targetLanguage: string
  ): TranslatedData {
    // Check if translation is supported
    if (!businessDataTranslator.isLanguageSupported(targetLanguage)) {
      throw new Error(`Language ${targetLanguage} is not supported`);
    }
    
    // Translate the business data
    const translatedData = businessDataTranslator.translate(data, targetLanguage);
    
    // Validate translated structure
    const isValid = businessDataTranslator.validateTranslation(translatedData);
    
    if (!isValid) {
      // Fallback to original data
      return businessDataTranslator.createFallback(data, targetLanguage);
    }
    
    return translatedData;
  }
  
  // Using validation helpers
  static validateBusinessRules(data: any): ValidationResult {
    const rules = [
      validationHelpers.required('companyName'),
      validationHelpers.email('contactEmail'),
      validationHelpers.minLength('description', 10),
      validationHelpers.maxLength('description', 500),
      validationHelpers.pattern('phone', /^\+?[\d\s\-\(\)]+$/),
      validationHelpers.range('employees', 1, 10000),
      validationHelpers.custom('website', (value: string) => {
        if (!value) return true;
        try {
          new URL(value);
          return true;
        } catch {
          return false;
        }
      }, 'Invalid URL format')
    ];
    
    return validationHelpers.validate(data, rules);
  }
  
  // Complex form field generation using utilities
  static generateDynamicFormFields(
    businessType: string,
    locale: string
  ): FormField[] {
    // Get base fields for business type
    const baseFields = formHelpers.getFieldsForBusinessType(businessType);
    
    // Translate field labels and placeholders
    const translatedFields = baseFields.map(field => ({
      ...field,
      label: businessDataTranslator.translateLabel(field.label, locale),
      placeholder: field.placeholder 
        ? businessDataTranslator.translateLabel(field.placeholder, locale)
        : undefined,
      helpText: field.helpText
        ? businessDataTranslator.translateLabel(field.helpText, locale)
        : undefined
    }));
    
    // Add conditional fields based on business type
    if (businessType === 'retail') {
      translatedFields.push(
        formHelpers.createField({
          id: 'storeLocations',
          type: 'number',
          label: businessDataTranslator.translateLabel('Number of Store Locations', locale),
          required: true,
          min: 1
        })
      );
    } else if (businessType === 'online') {
      translatedFields.push(
        formHelpers.createField({
          id: 'monthlyTraffic',
          type: 'number',
          label: businessDataTranslator.translateLabel('Monthly Website Traffic', locale),
          required: false,
          min: 0
        })
      );
    }
    
    return translatedFields;
  }
  
  // Data processing pipeline
  static async processBusinessApplication(
    applicationData: any,
    businessData: BusinessData
  ): Promise<ProcessedFormData> {
    // Step 1: Validate incoming data
    const validation = this.validateBusinessRules(applicationData);
    if (!validation.isValid) {
      throw new Error(`Invalid application data: ${validation.errors.join(', ')}`);
    }
    
    // Step 2: Merge with business data
    const mergedData = dataProcessor.mergeWithBusinessData(
      applicationData,
      businessData
    );
    
    // Step 3: Apply business-specific transformations
    const transformedData = dataProcessor.applyBusinessRules(
      mergedData,
      businessData.type
    );
    
    // Step 4: Calculate derived fields
    const enrichedData = dataProcessor.calculateDerivedFields(transformedData);
    
    // Step 5: Format for submission
    const formattedData = formHelpers.formatForSubmission(enrichedData);
    
    // Step 6: Add audit trail
    return dataProcessor.addAuditTrail(formattedData, {
      processedBy: 'CorrectUtilityUsage',
      timestamp: new Date().toISOString(),
      version: '1.0'
    });
  }
  
  // Helper method for form field configuration
  static configureFormField(
    baseField: FormField,
    options: {
      required?: boolean;
      validation?: any;
      conditional?: (data: any) => boolean;
      transform?: (value: any) => any;
    }
  ): FormField {
    const configuredField = { ...baseField };
    
    if (options.required !== undefined) {
      configuredField.required = options.required;
    }
    
    if (options.validation) {
      configuredField.validation = validationHelpers.combineValidations(
        configuredField.validation,
        options.validation
      );
    }
    
    if (options.conditional) {
      configuredField.conditional = options.conditional;
    }
    
    if (options.transform) {
      configuredField.transform = options.transform;
    }
    
    return configuredField;
  }
}

// Example usage functions
export function createBusinessForm(businessType: string, locale: string = 'en') {
  const fields = CorrectUtilityUsage.generateDynamicFormFields(businessType, locale);
  
  // Apply specific configurations
  const configuredFields = fields.map(field => {
    if (field.id === 'email') {
      return CorrectUtilityUsage.configureFormField(field, {
        validation: validationHelpers.email(),
        transform: (value: string) => value.toLowerCase().trim()
      });
    }
    
    if (field.id === 'phone') {
      return CorrectUtilityUsage.configureFormField(field, {
        validation: validationHelpers.phone(),
        transform: (value: string) => value.replace(/\D/g, '')
      });
    }
    
    return field;
  });
  
  return configuredFields;
}

export async function submitBusinessApplication(
  formData: Record<string, any>,
  businessData: BusinessData
): Promise<ProcessedFormData> {
  try {
    // Process the form submission
    const processedData = CorrectUtilityUsage.processFormSubmission(formData);
    
    // Apply business logic
    const finalData = await CorrectUtilityUsage.processBusinessApplication(
      processedData,
      businessData
    );
    
    return finalData;
  } catch (error) {
    console.error('Application submission failed:', error);
    throw error;
  }
}