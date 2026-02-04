import { describe, it, expect } from 'vitest';

/**
 * These tests verify that all service modules can be imported without syntax errors.
 * This catches issues like missing commas in object methods that break the entire module.
 */
describe('Service Module Imports (Syntax Validation)', () => {
  it('should import authService without errors', async () => {
    const module = await import('@/lib/services/authService');
    expect(module.authService).toBeDefined();
    expect(typeof module.authService.login).toBe('function');
    expect(typeof module.authService.signup).toBe('function');
    expect(typeof module.authService.verifyEmail).toBe('function');
    expect(typeof module.authService.getProfile).toBe('function');
    expect(typeof module.authService.updateProfile).toBe('function');
  });

  it('should import sessionService without errors', async () => {
    const module = await import('@/lib/services/sessionService');
    expect(module.sessionService).toBeDefined();
    expect(typeof module.sessionService.createSession).toBe('function');
    expect(typeof module.sessionService.listSessions).toBe('function');
    expect(typeof module.sessionService.getMessages).toBe('function');
    expect(typeof module.sessionService.startSession).toBe('function');
    expect(typeof module.sessionService.sendMessage).toBe('function');
    expect(typeof module.sessionService.finalizeSession).toBe('function');
  });

  it('should import questionService without errors', async () => {
    const module = await import('@/lib/services/questionService');
    expect(module.questionService).toBeDefined();
    expect(typeof module.questionService.listQuestions).toBe('function');
    expect(typeof module.questionService.getQuestion).toBe('function');
    expect(typeof module.questionService.getQuestionCoverage).toBe('function');
  });

  it('should import analyticsService without errors', async () => {
    const module = await import('@/lib/services/analyticsService');
    expect(module.analyticsService).toBeDefined();
    expect(typeof module.analyticsService.getSessionResults).toBe('function');
  });

  it('should import aiService without errors', async () => {
    const module = await import('@/lib/services/aiService');
    expect(module.aiService).toBeDefined();
    expect(typeof module.aiService.getStatus).toBe('function');
    expect(typeof module.aiService.chat).toBe('function');
    expect(typeof module.aiService.generateSpeech).toBe('function');
  });

  it('should import apiClient without errors', async () => {
    const module = await import('@/lib/api');
    expect(module.apiClient).toBeDefined();
    expect(typeof module.apiClient.get).toBe('function');
    expect(typeof module.apiClient.post).toBe('function');
    expect(typeof module.apiClient.put).toBe('function');
    expect(typeof module.apiClient.patch).toBe('function');
    expect(typeof module.apiClient.delete).toBe('function');
  });
});
