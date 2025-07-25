// Correct imports from lavi_specs services
import { emailService } from '../services/emailService';
import { dataService } from '../services/dataService';
import { validationService } from '../services/validationService';
import { notificationService } from '../services/notificationService';
import { analyticsService } from '../services/analyticsService';

// Example of correct service integration with proper async/await patterns
export class CorrectServiceIntegration {
  
  // Using emailService correctly
  static async sendBusinessApplicationEmail(applicationData) {
    try {
      // Validate email data first
      const isValid = await validationService.validateEmailData({
        to: applicationData.email,
        subject: 'Business Application Received',
        templateId: 'business_application'
      });
      
      if (!isValid) {
        throw new Error('Invalid email data');
      }
      
      // Prepare email content
      const emailContent = {
        to: applicationData.email,
        subject: 'Your Business Application Has Been Received',
        template: 'business_application',
        data: {
          applicantName: applicationData.fullName,
          businessName: applicationData.companyName,
          applicationId: applicationData.id,
          submittedDate: new Date().toLocaleDateString()
        }
      };
      
      // Send email using the service
      const result = await emailService.send(emailContent);
      
      // Track email sent
      await analyticsService.track('email_sent', {
        type: 'business_application',
        recipient: applicationData.email,
        success: result.success
      });
      
      return result;
    } catch (error) {
      console.error('Failed to send application email:', error);
      
      // Log error to analytics
      await analyticsService.trackError('email_send_failed', {
        error: error.message,
        context: 'business_application'
      });
      
      throw error;
    }
  }
  
  // Using dataService correctly with proper error handling
  static async fetchBusinessData(businessId) {
    try {
      // Check cache first
      const cachedData = await dataService.getFromCache(`business_${businessId}`);
      
      if (cachedData && !this.isDataStale(cachedData)) {
        await analyticsService.track('cache_hit', { 
          type: 'business_data',
          businessId 
        });
        return cachedData;
      }
      
      // Fetch fresh data
      const freshData = await dataService.fetchBusinessById(businessId);
      
      if (!freshData) {
        throw new Error(`Business not found: ${businessId}`);
      }
      
      // Update cache
      await dataService.setCache(`business_${businessId}`, freshData, {
        ttl: 3600 // 1 hour
      });
      
      // Track data fetch
      await analyticsService.track('data_fetched', {
        type: 'business_data',
        businessId,
        source: 'api'
      });
      
      return freshData;
    } catch (error) {
      console.error('Failed to fetch business data:', error);
      
      // Try fallback data source
      try {
        const fallbackData = await dataService.getFallbackData(businessId);
        if (fallbackData) {
          return fallbackData;
        }
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
      }
      
      throw error;
    }
  }
  
  // Complex workflow using multiple services
  static async processBusinessApplication(applicationData) {
    const processId = `process_${Date.now()}`;
    
    try {
      // Start tracking the process
      await analyticsService.startProcess(processId, 'business_application');
      
      // Step 1: Validate application data
      const validationResult = await validationService.validateBusinessApplication(
        applicationData
      );
      
      if (!validationResult.isValid) {
        throw new Error(`Validation failed: ${validationResult.errors.join(', ')}`);
      }
      
      // Step 2: Save application data
      const savedApplication = await dataService.saveApplication(applicationData);
      
      // Step 3: Send confirmation email
      await this.sendBusinessApplicationEmail(savedApplication);
      
      // Step 4: Send internal notification
      await notificationService.notifyAdmins({
        type: 'new_application',
        priority: 'normal',
        data: {
          applicationId: savedApplication.id,
          businessName: savedApplication.companyName,
          submittedBy: savedApplication.fullName
        }
      });
      
      // Step 5: Update analytics
      await analyticsService.track('application_processed', {
        applicationId: savedApplication.id,
        processingTime: Date.now() - parseInt(processId.split('_')[1])
      });
      
      // Complete the process tracking
      await analyticsService.completeProcess(processId, 'success');
      
      return {
        success: true,
        applicationId: savedApplication.id,
        message: 'Application processed successfully'
      };
      
    } catch (error) {
      // Track the failure
      await analyticsService.completeProcess(processId, 'failure', {
        error: error.message
      });
      
      // Send error notification
      await notificationService.notifyAdmins({
        type: 'application_error',
        priority: 'high',
        data: {
          error: error.message,
          applicationData: applicationData
        }
      }).catch(console.error); // Don't let notification failure break the flow
      
      throw error;
    }
  }
  
  // Batch processing with proper async handling
  static async processBatchApplications(applications) {
    const results = {
      successful: [],
      failed: []
    };
    
    // Process in chunks to avoid overwhelming the system
    const chunkSize = 10;
    const chunks = [];
    
    for (let i = 0; i < applications.length; i += chunkSize) {
      chunks.push(applications.slice(i, i + chunkSize));
    }
    
    for (const chunk of chunks) {
      // Process chunk in parallel
      const chunkResults = await Promise.allSettled(
        chunk.map(app => this.processBusinessApplication(app))
      );
      
      chunkResults.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          results.successful.push({
            application: chunk[index],
            result: result.value
          });
        } else {
          results.failed.push({
            application: chunk[index],
            error: result.reason.message
          });
        }
      });
      
      // Small delay between chunks
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Send summary notification
    await notificationService.notifyAdmins({
      type: 'batch_processing_complete',
      priority: 'normal',
      data: {
        total: applications.length,
        successful: results.successful.length,
        failed: results.failed.length
      }
    });
    
    return results;
  }
  
  // Helper methods
  static isDataStale(data) {
    if (!data || !data.lastUpdated) {
      return true;
    }
    
    const staleThreshold = 60 * 60 * 1000; // 1 hour
    const dataAge = Date.now() - new Date(data.lastUpdated).getTime();
    
    return dataAge > staleThreshold;
  }
  
  // Real-time updates using services
  static async subscribeToBusinessUpdates(businessId, callback) {
    try {
      // Subscribe to real-time updates
      const subscription = await dataService.subscribe(
        `business.${businessId}`,
        async (update) => {
          // Validate the update
          const isValid = await validationService.validateUpdate(update);
          
          if (!isValid) {
            console.warn('Received invalid update:', update);
            return;
          }
          
          // Track the update
          await analyticsService.track('realtime_update_received', {
            businessId,
            updateType: update.type
          });
          
          // Call the callback with processed update
          callback({
            ...update,
            processed: true,
            timestamp: new Date().toISOString()
          });
        }
      );
      
      return subscription;
    } catch (error) {
      console.error('Failed to subscribe to updates:', error);
      throw error;
    }
  }
}

// Export individual functions for direct use
export async function sendApplicationEmail(data) {
  return CorrectServiceIntegration.sendBusinessApplicationEmail(data);
}

export async function processApplication(data) {
  return CorrectServiceIntegration.processBusinessApplication(data);
}

export async function processBatch(applications) {
  return CorrectServiceIntegration.processBatchApplications(applications);
}

// Example usage
async function exampleUsage() {
  try {
    // Single application
    const applicationResult = await processApplication({
      fullName: 'John Doe',
      email: 'john@example.com',
      companyName: 'Acme Corp',
      industry: 'technology'
    });
    
    console.log('Application processed:', applicationResult);
    
    // Batch processing
    const batchResults = await processBatch([
      { fullName: 'Jane Smith', email: 'jane@example.com', companyName: 'Tech Co' },
      { fullName: 'Bob Johnson', email: 'bob@example.com', companyName: 'Sales Inc' }
    ]);
    
    console.log('Batch results:', batchResults);
    
  } catch (error) {
    console.error('Example failed:', error);
  }
}