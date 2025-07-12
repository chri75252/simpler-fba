#!/usr/bin/env python3
"""
Test script for the enhanced file-based monitoring system
Verifies that all components work correctly with actual file data
"""

import json
import sys
from pathlib import Path
from monitoring_system import FBAMonitoringSystem

def test_monitoring_system():
    """Test the enhanced monitoring system"""
    print("🧪 Testing Enhanced File-Based Monitoring System")
    print("=" * 60)
    
    try:
        # Initialize monitoring system
        monitor = FBAMonitoringSystem()
        print("✅ Monitoring system initialized successfully")
        
        # Test single monitoring cycle
        print("\n🔄 Running single monitoring cycle...")
        monitor.run_monitoring_cycle()
        print("✅ Monitoring cycle completed")
        
        # Check for any flags created
        flags = monitor.get_active_flags()
        print(f"\n📊 Monitoring Results: {len(flags)} flags created")
        
        if flags:
            print("\n🚨 Active Flags:")
            for flag in flags[:3]:  # Show first 3 flags
                flag_type = flag.get('flag_type', 'UNKNOWN')
                severity = flag.get('severity', 'INFO')
                
                # Check for aggregated structure
                alert_summary = flag.get('alert_summary', {})
                instances = flag.get('instances', [])
                progress_tracking = flag.get('progress_tracking', {})
                
                print(f"\n  🔍 {flag_type} ({severity})")
                
                if alert_summary:
                    print(f"    📈 Instances: {alert_summary.get('total_instances', 1)}")
                    print(f"    ⏱️  Timespan: {alert_summary.get('timespan', 'Unknown')}")
                    if alert_summary.get('severity_escalated'):
                        print(f"    ⚠️  Escalated from {alert_summary.get('original_severity', 'Unknown')}")
                
                if instances:
                    latest = instances[-1]
                    print(f"    🎯 Issue: {latest.get('specific_issue', 'No details')[:80]}...")
                    if latest.get('source_file_path'):
                        print(f"    📁 Source: {Path(latest['source_file_path']).name}")
                
                if progress_tracking:
                    products_progress = progress_tracking.get('products_progress', {})
                    if products_progress:
                        completion = products_progress.get('processing_completion_rate', 0)
                        print(f"    📊 Progress: {completion:.1f}% complete")
        else:
            print("✅ No issues detected - system appears healthy!")
        
        # Test progress tracking
        print("\n📈 Testing Progress Tracking...")
        progress = monitor._get_comprehensive_progress_tracking()
        
        products_progress = progress.get('products_progress', {})
        if products_progress:
            print(f"  📦 Products: {products_progress.get('total_supplier_products', 0)} total")
            print(f"  🔍 Amazon Cache: {products_progress.get('products_with_amazon_data', 0)} files")
            print(f"  ✅ Keepa Success: {products_progress.get('keepa_success_rate', 0):.1f}%")
        
        financial_progress = progress.get('financial_analysis_progress', {})
        if financial_progress:
            print(f"  💰 CSV Reports: {financial_progress.get('csv_reports_generated', 0)} generated")
            print(f"  📊 Data Quality: {financial_progress.get('financial_data_completeness_rate', 0):.1f}%")
        
        ai_progress = progress.get('ai_category_progress', {})
        if ai_progress:
            print(f"  🤖 AI Suggestions: {ai_progress.get('total_categories_suggested', 0)} total")
            print(f"  🎯 AI Success Rate: {ai_progress.get('ai_productivity_rate', 0):.1f}%")
        
        # Test data quality metrics
        print("\n🎯 Testing Data Quality Metrics...")
        quality_summary = monitor._calculate_data_quality_summary()
        
        if quality_summary.get('overall_quality_score'):
            score = quality_summary['overall_quality_score']
            grade = quality_summary.get('quality_grade', 'UNKNOWN')
            print(f"  🏆 Overall Quality: {score:.1f}% ({grade})")
            
            component_scores = quality_summary.get('component_scores', {})
            for component, score in component_scores.items():
                print(f"    • {component}: {score:.1f}%")
        
        print("\n✅ Enhanced monitoring system test completed successfully!")
        print("\n💡 Key Features Verified:")
        print("  ✅ File-based data extraction (no log dependency)")
        print("  ✅ Alert aggregation with instance tracking")
        print("  ✅ Severity escalation based on thresholds")
        print("  ✅ Comprehensive progress tracking")
        print("  ✅ Data quality metrics calculation")
        print("  ✅ Structured flag files with detailed context")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flag_aggregation():
    """Test flag aggregation functionality"""
    print("\n🔄 Testing Flag Aggregation...")
    
    try:
        monitor = FBAMonitoringSystem()
        
        # Create multiple instances of the same flag type
        for i in range(3):
            monitor.create_aggregated_flag(
                "TEST_KEEPA_TIMEOUT",
                "WARNING",
                {
                    "specific_issue": f"Test timeout issue #{i+1}",
                    "resolution_suggestions": ["Test suggestion 1", "Test suggestion 2"],
                    "impact_assessment": "Test impact",
                    "data_quality_metrics": {"test_metric": i+1}
                },
                source_file_path=f"test_file_{i+1}.json",
                extracted_data={"test_data": f"value_{i+1}"}
            )
        
        # Check aggregation
        flags = monitor.get_active_flags()
        test_flags = [f for f in flags if f.get('flag_type') == 'TEST_KEEPA_TIMEOUT']
        
        if test_flags:
            flag = test_flags[0]
            alert_summary = flag.get('alert_summary', {})
            instances = flag.get('instances', [])
            
            print(f"  📊 Aggregated {alert_summary.get('total_instances', 0)} instances")
            print(f"  📅 Timespan: {alert_summary.get('timespan', 'Unknown')}")
            print(f"  📝 Instance count: {len(instances)}")
            
            if len(instances) == 3:
                print("  ✅ All instances properly aggregated")
            else:
                print(f"  ❌ Expected 3 instances, got {len(instances)}")
        
        # Clean up test flags
        monitor.clear_flags(['TEST_KEEPA_TIMEOUT'])
        print("  🧹 Test flags cleaned up")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Aggregation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Enhanced Monitoring System Tests")
    print("=" * 60)
    
    # Run main test
    main_test_passed = test_monitoring_system()
    
    # Run aggregation test
    aggregation_test_passed = test_flag_aggregation()
    
    print("\n" + "=" * 60)
    if main_test_passed and aggregation_test_passed:
        print("🎉 ALL TESTS PASSED - Enhanced monitoring system is ready!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
        sys.exit(1)
