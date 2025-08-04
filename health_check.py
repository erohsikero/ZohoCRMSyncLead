#!/usr/bin/env python3

"""
Health check script for the running application
"""

import requests
import json
import sys
from datetime import datetime

def check_health():
    """Check application health"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Application is healthy")
            print(f"📊 Status: {data['status']}")
            print(f"🕒 Timestamp: {data['timestamp']}")
            print(f"⚡ Scheduler: {'Running' if data['scheduler_running'] else 'Stopped'}")
            return True
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to application (is it running?)")
        print("💡 Start the application with: ./start.sh")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def check_sync_status():
    """Check sync status"""
    try:
        response = requests.get("http://localhost:8000/sync-status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("\n📊 Sync Status:")
            print(f"⚡ Scheduler: {'Running' if data['scheduler_running'] else 'Stopped'}")
            print(f"🕒 Current Time: {data['current_time']}")
            
            if data['jobs']:
                print("\n📅 Scheduled Jobs:")
                for job in data['jobs']:
                    next_run = job['next_run_time']
                    if next_run:
                        next_run = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                        print(f"  • {job['name']}")
                        print(f"    Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    else:
                        print(f"  • {job['name']}: Not scheduled")
            else:
                print("⚠️  No scheduled jobs found")
            
            return True
        else:
            print(f"❌ Sync status check failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Sync status error: {e}")
        return False

def main():
    """Main health check"""
    print("🏥 Application Health Check")
    print("=" * 30)
    
    health_ok = check_health()
    
    if health_ok:
        sync_ok = check_sync_status()
        
        if health_ok and sync_ok:
            print("\n🎉 All systems operational!")
            print("🌐 Dashboard: http://localhost:8000")
            sys.exit(0)
        else:
            print("\n⚠️  Some issues detected")
            sys.exit(1)
    else:
        print("\n❌ Application not healthy")
        sys.exit(1)

if __name__ == "__main__":
    main()
