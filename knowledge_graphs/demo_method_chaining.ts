// Demo TypeScript file to showcase method chaining validation
import { z } from 'zod';
import * as yup from 'yup';
import Joi from 'joi';

// ===== Zod Examples =====

// Valid Zod method chains
const validEmail = z.string().email().min(5);
const validAge = z.number().positive().int().max(120);
const validUser = z.object({
    name: z.string().min(2).max(50),
    email: z.string().email(),
    age: z.number().min(18).optional(),
    isActive: z.boolean().default(true)
}).strict().partial();

// Complex valid chains
const complexSchema = z.string()
    .email()
    .refine(val => val.includes('@company.com'))
    .transform(val => val.toLowerCase())
    .optional()
    .nullable();

// Invalid Zod method chains (these should be flagged as errors)
const invalidChain1 = z.string().positive();  // ❌ positive is for numbers
const invalidChain2 = z.number().email();     // ❌ email is for strings  
const invalidChain3 = z.boolean().min(5);     // ❌ min is not for booleans
const invalidChain4 = z.string().notAMethod(); // ❌ method doesn't exist

// ===== Yup Examples =====

// Valid Yup method chains
const yupString = yup.string().email().required().min(5);
const yupNumber = yup.number().positive().integer().max(100);
const yupObject = yup.object({
    name: yup.string().required(),
    age: yup.number().min(0).max(120)
}).strict();

// Invalid Yup chains (if validator has Yup support)
const yupInvalid1 = yup.string().positive();  // ❌ positive is for numbers
const yupInvalid2 = yup.number().email();     // ❌ email is for strings

// ===== Joi Examples =====

// Valid Joi method chains
const joiString = Joi.string().email().min(5).required();
const joiNumber = Joi.number().positive().integer().max(100);
const joiObject = Joi.object({
    username: Joi.string().alphanum().min(3).max(30).required(),
    email: Joi.string().email()
});

// Invalid Joi chains (if validator has Joi support)
const joiInvalid1 = Joi.string().positive();  // ❌ positive is for numbers
const joiInvalid2 = Joi.number().email();     // ❌ email is for strings

// ===== Edge Cases =====

// Nested schemas
const nestedSchema = z.object({
    user: z.object({
        profile: z.object({
            email: z.string().email().toLowerCase()
        }).optional()
    }),
    items: z.array(z.string().min(1)).min(1).max(10)
});

// Union types
const unionSchema = z.union([
    z.string().email(),
    z.string().url()
]).optional();

// Discriminated unions
const discriminatedUnion = z.discriminatedUnion("type", [
    z.object({ type: z.literal("email"), value: z.string().email() }),
    z.object({ type: z.literal("phone"), value: z.string().regex(/^\d{10}$/) })
]);

// Transform and refine chains
const transformChain = z.string()
    .transform(val => val.trim())
    .refine(val => val.length > 0)
    .transform(val => val.toUpperCase());

console.log("Method chaining demo - check validation results!");