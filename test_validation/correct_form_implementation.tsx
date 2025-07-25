import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

// Correct imports from lavi_specs project
import { FormInput } from '../components/form/FormInput';
import { FormSelect } from '../components/form/FormSelect';
import { FormCheckbox } from '../components/form/FormCheckbox';
import { FormField, FormSection } from '../types';

// Define proper validation schema
const formSchema = z.object({
  firstName: z.string().min(2, 'First name must be at least 2 characters'),
  lastName: z.string().min(2, 'Last name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  role: z.string().min(1, 'Please select a role'),
  acceptTerms: z.boolean().refine(val => val === true, {
    message: 'You must accept the terms and conditions'
  })
});

type FormData = z.infer<typeof formSchema>;

interface CorrectFormImplementationProps {
  onSubmit: (data: FormData) => void;
  defaultValues?: Partial<FormData>;
}

export const CorrectFormImplementation: React.FC<CorrectFormImplementationProps> = ({ 
  onSubmit, 
  defaultValues 
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const {
    register,
    handleSubmit,
    formState: { errors },
    control
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: defaultValues || {
      firstName: '',
      lastName: '',
      email: '',
      role: '',
      acceptTerms: false
    }
  });

  const handleFormSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      await onSubmit(data);
    } catch (error) {
      console.error('Form submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Define form fields using correct types
  const personalInfoSection: FormSection = {
    id: 'personal-info',
    title: 'Personal Information',
    fields: [
      {
        id: 'firstName',
        type: 'text',
        label: 'First Name',
        required: true,
        placeholder: 'Enter your first name'
      },
      {
        id: 'lastName',
        type: 'text',
        label: 'Last Name',
        required: true,
        placeholder: 'Enter your last name'
      },
      {
        id: 'email',
        type: 'email',
        label: 'Email Address',
        required: true,
        placeholder: 'your.email@example.com'
      }
    ]
  };

  const roleOptions = [
    { value: 'developer', label: 'Developer' },
    { value: 'designer', label: 'Designer' },
    { value: 'manager', label: 'Manager' },
    { value: 'other', label: 'Other' }
  ];

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">{personalInfoSection.title}</h2>
        
        <FormInput
          name="firstName"
          label="First Name"
          type="text"
          register={register}
          error={errors.firstName}
          required
          placeholder="Enter your first name"
        />

        <FormInput
          name="lastName"
          label="Last Name"
          type="text"
          register={register}
          error={errors.lastName}
          required
          placeholder="Enter your last name"
        />

        <FormInput
          name="email"
          label="Email Address"
          type="email"
          register={register}
          error={errors.email}
          required
          placeholder="your.email@example.com"
        />

        <FormSelect
          name="role"
          label="Your Role"
          options={roleOptions}
          register={register}
          error={errors.role}
          required
          placeholder="Select your role"
        />

        <FormCheckbox
          name="acceptTerms"
          label="I accept the terms and conditions"
          register={register}
          error={errors.acceptTerms}
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Submitting...' : 'Submit Form'}
      </button>
    </form>
  );
};

export default CorrectFormImplementation;