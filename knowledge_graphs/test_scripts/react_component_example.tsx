import React, { useState, useEffect, useCustomHook } from 'react';
import { Button, Modal } from '@mui/material';
import { UserProfile, UserSettings } from '../types/user';
import { fetchUserData, updateUserProfile } from '../api/users';
import { validateEmail, formatDate } from '../utils/helpers';

// This component has several intentional hallucinations for testing:
// 1. useCustomHook doesn't exist in React
// 2. UserProfile and UserSettings types are not defined
// 3. fetchUserData and updateUserProfile functions don't exist
// 4. validateEmail and formatDate are made up utilities

interface ProfileFormProps {
  userId: string;
  onSave: (profile: UserProfile) => void;
  settings?: UserSettings;
}

const ProfileForm: React.FC<ProfileFormProps> = ({ userId, onSave, settings }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  
  // Hallucination: useCustomHook doesn't exist
  const customValue = useCustomHook(userId);
  
  useEffect(() => {
    const loadProfile = async () => {
      setLoading(true);
      try {
        // Hallucination: fetchUserData doesn't exist
        const data = await fetchUserData(userId);
        setProfile(data);
      } catch (error) {
        console.error('Failed to load profile:', error);
      } finally {
        setLoading(false);
      }
    };
    
    loadProfile();
  }, [userId]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!profile) return;
    
    // Hallucination: validateEmail doesn't exist
    if (!validateEmail(profile.email)) {
      alert('Invalid email address');
      return;
    }
    
    try {
      // Hallucination: updateUserProfile doesn't exist
      const updated = await updateUserProfile(userId, profile);
      onSave(updated);
      setShowModal(true);
    } catch (error) {
      console.error('Failed to update profile:', error);
    }
  };
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  return (
    <>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          value={profile?.email || ''}
          onChange={(e) => setProfile(prev => ({ ...prev!, email: e.target.value }))}
        />
        
        <input
          type="text"
          value={profile?.name || ''}
          onChange={(e) => setProfile(prev => ({ ...prev!, name: e.target.value }))}
        />
        
        {/* Hallucination: formatDate doesn't exist */}
        <p>Member since: {profile?.createdAt ? formatDate(profile.createdAt) : 'Unknown'}</p>
        
        <Button type="submit" variant="contained">
          Save Profile
        </Button>
      </form>
      
      <Modal open={showModal} onClose={() => setShowModal(false)}>
        <div>Profile updated successfully!</div>
      </Modal>
    </>
  );
};

export default ProfileForm;