// Importing real types but adding non-existent ones
import { 
  FormField,
  FormFieldAdvanced,    // Non-existent type
  ValidationRule,       // Non-existent type
  Theme,
  ThemeAdvanced        // Non-existent type
} from '@/types';

// Non-existent enum
export enum FormFieldType {
  TEXT = 'text',
  NUMBER = 'number',
  DATE = 'date',
  COLOR = 'color',
  SLIDER = 'slider',
  MATRIX = 'matrix',      // Non-existent value
  QUANTUM = 'quantum'     // Non-existent value
}

// Non-existent interface
export interface FormValidationOptions {
  mode: 'lazy' | 'eager' | 'aggressive';
  debounceMs: number;
  showErrorsOnBlur: boolean;
  cascadeValidation: boolean;
  asyncValidators?: Array<(value: any) => Promise<boolean>>;
}

// Real interface with non-existent properties
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  age: number;
  // Non-existent properties
  quantumState: 'superposition' | 'collapsed';
  neuralNetworkId: string;
  blockchainAddress: string;
  holographicAvatar: {
    url: string;
    resolution: '4K' | '8K' | '16K';
    format: 'H3D' | 'QVR';
  };
}

// Non-existent type alias
export type ValidationEngine = {
  validate: (data: any) => Promise<ValidationResult>;
  clearErrors: () => void;
  setCustomValidator: (field: string, validator: ValidationRule) => void;
  enableQuantumValidation: (enabled: boolean) => void;
};

// Non-existent generic type
export type FormFieldMapping<T> = {
  [K in keyof T]: FormFieldAdvanced<T[K]>;
};

// Extending real type with non-existent properties
export interface ExtendedTheme extends Theme {
  animations: {
    formTransitions: string;
    hoverEffects: string;
    quantumEffects: string;
  };
  neuralColors: {
    synaptic: string;
    dendrite: string;
    axon: string;
  };
  dimensions: {
    holographicDepth: number;
    temporalOffset: number;
  };
}

// Non-existent utility type
export type DeepPartialWithValidation<T> = {
  [P in keyof T]?: T[P] extends object 
    ? DeepPartialWithValidation<T[P]> & { _validation?: ValidationRule }
    : T[P] | { value: T[P]; validation: ValidationRule };
};

// Non-existent namespace
export namespace FormUtils {
  export function validateQuantumField(value: any): boolean {
    return true;
  }

  export function applyNeuralTransform(data: any): any {
    return data;
  }

  export interface QuantumFormState {
    superposition: boolean;
    entangled: string[];
    probability: number;
  }
}

// Non-existent decorator type
export type FormDecorator = {
  memoizeQuantum: boolean;
  enableTimeTrave: boolean;
  neuromorphicOptimization: 'enabled' | 'disabled' | 'auto';
};