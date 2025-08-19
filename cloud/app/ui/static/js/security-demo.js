/**
 * Security Demo JavaScript - Demonstrates before/after security implementation
 */

class SecurityDemo {
    constructor() {
        this.isRunning = false;
        this.demoData = {
            phases: [],
            currentPhase: null,
            timeline: [],
            comparison: {}
        };
        this.demoInterval = null;
        this.demoStartTime = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        const startButton = document.getElementById('start-demo');
        const stopButton = document.getElementById('stop-demo');
        
        if (startButton) {
            startButton.addEventListener('click', () => this.startDemo());
        }
        
        if (stopButton) {
            stopButton.addEventListener('click', () => this.stopDemo());
        }
    }
    
    async startDemo() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.demoStartTime = new Date();
        
        // Update UI
        document.getElementById('start-demo').classList.add('d-none');
        document.getElementById('stop-demo').classList.remove('d-none');
        document.getElementById('demo-results').classList.remove('d-none');
        
        // Initialize demo chart
        if (window.chartManager) {
            window.chartManager.initSecurityDemoChart();
        }
        
        // Show progress
        this.showDemoProgress();
        
        try {
            // Phase 1: No Security (60 seconds)
            await this.runPhase1();
            
            // Phase 2: Full Security (60 seconds)
            await this.runPhase2();
            
            // Complete demo
            this.completeDemo();
            
        } catch (error) {
            console.error('Demo error:', error);
            this.showError('Demo failed: ' + error.message);
            this.stopDemo();
        }
    }
    
    async runPhase1() {
        this.updateDemoStatus('Phase 1: Collecting data without security measures...');
        
        // Simulate disabling security
        await this.updateSecuritySettings(false);
        
        // Run phase for 60 seconds
        const phaseData = await this.runPhaseWithAttacks('insecure', 60);
        
        this.demoData.phases.push({
            name: 'No Security',
            duration: 60,
            data: phaseData,
            security_enabled: false
        });
    }
    
    async runPhase2() {
        this.updateDemoStatus('Phase 2: Collecting data with full security measures...');
        
        // Simulate enabling security
        await this.updateSecuritySettings(true);
        
        // Run phase for 60 seconds
        const phaseData = await this.runPhaseWithAttacks('secure', 60);
        
        this.demoData.phases.push({
            name: 'Full Security',
            duration: 60,
            data: phaseData,
            security_enabled: true
        });
    }
    
    async runPhaseWithAttacks(mode, durationSeconds) {
        const phaseData = {
            total_messages: 0,
            valid_messages: 0,
            blocked_messages: 0,
            security_events: 0,
            attack_attempts: 0,
            timeline: []
        };
        
        const startTime = Date.now();
        const endTime = startTime + (durationSeconds * 1000);
        
        // Simulate attack scenarios
        const attacks = this.generateAttackScenarios(mode);
        
        while (Date.now() < endTime && this.isRunning) {
            const currentTime = Date.now();
            const elapsed = (currentTime - startTime) / 1000;
            
            // Simulate telemetry and attacks
            const periodData = await this.simulatePeriod(mode, attacks);
            
            // Update phase data
            phaseData.total_messages += periodData.messages;
            phaseData.valid_messages += periodData.valid;
            phaseData.blocked_messages += periodData.blocked;
            phaseData.security_events += periodData.security_events;
            phaseData.attack_attempts += periodData.attacks;
            
            // Add to timeline
            phaseData.timeline.push({
                timestamp: new Date(currentTime).toISOString(),
                elapsed_seconds: Math.floor(elapsed),
                messages_sent: periodData.messages,
                valid_messages: periodData.valid,
                messages_blocked: periodData.blocked,
                security_events: periodData.security_events
            });
            
            // Update progress
            const progress = (elapsed / durationSeconds) * 100;
            this.updatePhaseProgress(progress);
            
            // Update chart
            if (window.chartManager) {
                window.chartManager.updateSecurityDemoChart({
                    timeline: phaseData.timeline
                });
            }
            
            // Wait for next period (5 seconds)
            await this.sleep(5000);
        }
        
        return phaseData;
    }
    
    generateAttackScenarios(mode) {
        const baseAttacks = [
            {
                type: 'replay',
                frequency: mode === 'insecure' ? 0.3 : 0.1, // Higher success rate when insecure
                description: 'Message replay attack'
            },
            {
                type: 'spoofing',
                frequency: mode === 'insecure' ? 0.4 : 0.05,
                description: 'Message spoofing with invalid signature'
            },
            {
                type: 'dos',
                frequency: mode === 'insecure' ? 0.2 : 0.02,
                description: 'Denial of service attack'
            },
            {
                type: 'tampering',
                frequency: mode === 'insecure' ? 0.3 : 0.01,
                description: 'Message tampering attack'
            }
        ];
        
        return baseAttacks;
    }
    
    async simulatePeriod(mode, attacks) {
        const periodData = {
            messages: 0,
            valid: 0,
            blocked: 0,
            security_events: 0,
            attacks: 0
        };
        
        // Simulate normal telemetry messages
        const normalMessages = this.randomBetween(10, 20);
        periodData.messages += normalMessages;
        
        if (mode === 'secure') {
            // Most messages are valid with security
            periodData.valid += Math.floor(normalMessages * 0.95);
            periodData.blocked += normalMessages - periodData.valid;
        } else {
            // All messages pass without security
            periodData.valid += normalMessages;
        }
        
        // Simulate attacks
        for (const attack of attacks) {
            if (Math.random() < attack.frequency) {
                const attackMessages = this.randomBetween(5, 15);
                periodData.messages += attackMessages;
                periodData.attacks += 1;
                
                if (mode === 'secure') {
                    // Security blocks most attacks
                    const blocked = Math.floor(attackMessages * 0.9);
                    periodData.blocked += blocked;
                    periodData.valid += attackMessages - blocked;
                    periodData.security_events += 1;
                } else {
                    // No security, attacks succeed
                    periodData.valid += attackMessages;
                }
                
                // Log attack attempt
                console.log(`Simulated ${attack.type} attack: ${attackMessages} messages`);
            }
        }
        
        return periodData;
    }
    
    async updateSecuritySettings(enabled) {
        // This would normally call the fog service to update security settings
        // For demo purposes, we'll just simulate the API call
        
        try {
            // Simulate API call delay
            await this.sleep(2000);
            
            console.log(`Security settings updated: ${enabled ? 'ENABLED' : 'DISABLED'}`);
            
            // In a real implementation, this would:
            // - Update fog service configuration
            // - Enable/disable HMAC verification
            // - Enable/disable encryption
            // - Enable/disable rate limiting
            // - Enable/disable replay protection
            
        } catch (error) {
            console.error('Failed to update security settings:', error);
            throw error;
        }
    }
    
    completeDemo() {
        this.isRunning = false;
        
        // Calculate comparison
        this.calculateComparison();
        
        // Update UI
        this.updateDemoStatus('Demo completed successfully!');
        this.renderComparison();
        
        // Reset buttons
        document.getElementById('start-demo').classList.remove('d-none');
        document.getElementById('stop-demo').classList.add('d-none');
        
        dashboard.showSuccess('Security demo completed successfully!');
    }
    
    stopDemo() {
        this.isRunning = false;
        
        if (this.demoInterval) {
            clearInterval(this.demoInterval);
            this.demoInterval = null;
        }
        
        // Reset UI
        document.getElementById('start-demo').classList.remove('d-none');
        document.getElementById('stop-demo').classList.add('d-none');
        
        this.updateDemoStatus('Demo stopped');
    }
    
    calculateComparison() {
        if (this.demoData.phases.length < 2) return;
        
        const insecurePhase = this.demoData.phases[0];
        const securePhase = this.demoData.phases[1];
        
        this.demoData.comparison = {
            messages_sent: {
                insecure: insecurePhase.data.total_messages,
                secure: securePhase.data.total_messages
            },
            valid_messages: {
                insecure: insecurePhase.data.valid_messages,
                secure: securePhase.data.valid_messages
            },
            blocked_messages: {
                insecure: insecurePhase.data.blocked_messages,
                secure: securePhase.data.blocked_messages
            },
            security_events: {
                insecure: insecurePhase.data.security_events,
                secure: securePhase.data.security_events
            },
            attack_success_rate: {
                insecure: insecurePhase.data.attack_attempts > 0 ? 
                    (insecurePhase.data.valid_messages / insecurePhase.data.total_messages) * 100 : 0,
                secure: securePhase.data.attack_attempts > 0 ? 
                    (securePhase.data.valid_messages / securePhase.data.total_messages) * 100 : 0
            },
            protection_effectiveness: {
                replay_protection: securePhase.data.blocked_messages > insecurePhase.data.blocked_messages,
                signature_verification: securePhase.data.security_events > insecurePhase.data.security_events,
                rate_limiting: securePhase.data.blocked_messages > 0
            }
        };
    }
    
    renderComparison() {
        const container = document.getElementById('demo-comparison');
        if (!container || !this.demoData.comparison) return;
        
        const comparison = this.demoData.comparison;
        
        container.innerHTML = `
            <div class="demo-metrics">
                <div class="demo-metric">
                    <h4>${comparison.messages_sent.insecure}</h4>
                    <div class="text-muted">Messages (No Security)</div>
                </div>
                <div class="demo-metric">
                    <h4>${comparison.messages_sent.secure}</h4>
                    <div class="text-muted">Messages (With Security)</div>
                </div>
                <div class="demo-metric">
                    <h4>${comparison.blocked_messages.secure}</h4>
                    <div class="text-muted">Attacks Blocked</div>
                </div>
                <div class="demo-metric">
                    <h4>${comparison.security_events.secure}</h4>
                    <div class="text-muted">Security Events</div>
                </div>
            </div>
            
            <div class="mt-4">
                <h6>Security Improvements:</h6>
                <ul class="list-unstyled">
                    <li>
                        <i class="fas fa-shield-alt text-success me-2"></i>
                        <strong>Message Integrity:</strong> 
                        ${comparison.protection_effectiveness.signature_verification ? 'PROTECTED' : 'VULNERABLE'}
                    </li>
                    <li>
                        <i class="fas fa-redo text-success me-2"></i>
                        <strong>Replay Protection:</strong> 
                        ${comparison.protection_effectiveness.replay_protection ? 'PROTECTED' : 'VULNERABLE'}
                    </li>
                    <li>
                        <i class="fas fa-tachometer-alt text-success me-2"></i>
                        <strong>Rate Limiting:</strong> 
                        ${comparison.protection_effectiveness.rate_limiting ? 'ACTIVE' : 'INACTIVE'}
                    </li>
                </ul>
            </div>
        `;
    }
    
    showDemoProgress() {
        // This would show a progress indicator
        // For now, we'll just update the status
    }
    
    updateDemoStatus(status) {
        console.log('Demo Status:', status);
        
        // You could update a status element here
        // const statusElement = document.getElementById('demo-status');
        // if (statusElement) {
        //     statusElement.textContent = status;
        // }
    }
    
    updatePhaseProgress(progress) {
        console.log(`Phase Progress: ${Math.floor(progress)}%`);
        
        // Update progress bar if exists
        const progressBar = document.querySelector('.demo-progress .progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }
    
    randomBetween(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    showError(message) {
        if (dashboard) {
            dashboard.showError(message);
        } else {
            console.error(message);
        }
    }
}

// Initialize security demo when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.securityDemo = new SecurityDemo();
});