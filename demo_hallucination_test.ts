// Mix of correct code and hallucinations

import React from 'react';
import { z } from 'zod';

// CORRECT: Real TypeScript/JavaScript
const now = new Date();
const id = parseInt("123");
const users = data.filter(u => u.active);

// CORRECT: Zod method chaining  
const schema = z.string().email().min(5);
const numberSchema = z.number().positive();

// HALLUCINATION: Non-existent methods
const quantum = Array.quantumFilter();  // ❌ Should be detected
console.neural('Processing');           // ❌ Should be detected
const hash = Math.quantumRandom();      // ❌ Should be detected

// CORRECT: Service patterns
dataService.getFromCache('users');
emailService.send({ to: 'user@example.com' });

// HALLUCINATION: Made-up component
<FormSlider value={5} />                // ❌ Should be detected
