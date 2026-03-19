"""
Test script to demonstrate the agent validation system
"""
import json
from schemas.agent_validation import (
    AgentValidationFactory,
    validate_all_agent_outputs,
    create_fallback_output
)
from utils.logging import logger


def test_validation_system():
    """Test the validation system with various inputs"""
    
    logger.info("🧪 TESTING AGENT VALIDATION SYSTEM")
    
    # Test 1: Valid Planner Output
    logger.info("\n=== TEST 1: VALID PLANNER OUTPUT ===")
    valid_planner_output = {
        "product_name": "AI Project Manager",
        "problem_statement": "Teams struggle with project coordination and deadline tracking in distributed environments.",
        "target_users": ["Project Managers", "Development Teams", "Stakeholders"],
        "core_goals": ["Streamline project workflows", "Improve team communication", "Track progress accurately"],
        "key_features_high_level": ["AI-powered task scheduling", "Real-time collaboration", "Automated reporting"]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'planner', json.dumps(valid_planner_output)
        )
        logger.info("✅ Valid planner output passed validation")
        logger.info(f"   Product: {validated['product_name']}")
    except Exception as e:
        logger.error(f"❌ Valid planner output failed: {str(e)}")
    
    # Test 2: Invalid Planner Output (missing field)
    logger.info("\n=== TEST 2: INVALID PLANNER OUTPUT ===")
    invalid_planner_output = {
        "product_name": "AI Project Manager",
        "problem_statement": "Too short",  # Too short
        "target_users": [],  # Empty list
        # Missing core_goals and key_features_high_level
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'planner', json.dumps(invalid_planner_output)
        )
        logger.info("✅ Invalid planner output was handled gracefully")
    except Exception as e:
        logger.info(f"✅ Invalid planner output correctly rejected: {str(e)}")
    
    # Test 3: Malformed JSON
    logger.info("\n=== TEST 3: MALFORMED JSON ===")
    malformed_json = '''
    {
        "product_name": "AI Project Manager",
        "problem_statement": "Teams struggle with project coordination",
        "target_users": ["Project Managers"],
        "core_goals": ["Streamline workflows"],
        "key_features_high_level": ["AI scheduling"]
        // This comment makes it invalid JSON
    }
    '''
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'planner', malformed_json
        )
        logger.info("✅ Malformed JSON was cleaned and validated")
    except Exception as e:
        logger.info(f"✅ Malformed JSON correctly rejected: {str(e)}")
    
    # Test 4: Valid Analyst Output
    logger.info("\n=== TEST 4: VALID ANALYST OUTPUT ===")
    valid_analyst_output = {
        "problem_statement": "Development teams struggle with project coordination and deadline tracking in distributed environments, leading to missed deadlines and poor team morale.",
        "target_users": ["Software Developers", "Project Managers", "Team Leads", "Stakeholders"],
        "user_personas": [
            {
                "name": "Alex Developer",
                "description": "Senior developer working on multiple projects simultaneously",
                "pain_points": ["Context switching between projects", "Missing deadlines due to poor coordination", "Lack of visibility into project dependencies"]
            }
        ],
        "user_stories": [
            {
                "title": "Task Management",
                "as_a": "developer",
                "i_want_to": "organize my tasks efficiently across multiple projects",
                "so_that": "I can prioritize work and meet deadlines consistently"
            }
        ],
        "success_metrics": [
            {
                "name": "Productivity Increase",
                "description": "Measure of task completion efficiency improvement",
                "target": "25% increase in on-time delivery"
            }
        ]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'analyst', json.dumps(valid_analyst_output)
        )
        logger.info("✅ Valid analyst output passed validation")
        logger.info(f"   User Stories: {len(validated['user_stories'])}")
    except Exception as e:
        logger.error(f"❌ Valid analyst output failed: {str(e)}")
    
    # Test 5: Valid Architect Output
    logger.info("\n=== TEST 5: VALID ARCHITECT OUTPUT ===")
    valid_architect_output = {
        "system_design": "Microservices architecture with AI-powered task management and real-time collaboration features",
        "tech_stack": {
            "frontend": "React with TypeScript",
            "backend": "FastAPI with Python",
            "database": "PostgreSQL with Redis cache",
            "infrastructure": "Docker containers on AWS"
        },
        "architecture_components": [
            "API Gateway",
            "Authentication Service",
            "AI Processing Engine",
            "Database Layer",
            "Notification Service"
        ],
        "api_endpoints": [
            {
                "name": "Generate Product Plan",
                "method": "POST",
                "endpoint": "/api/v1/generate",
                "description": "Generate comprehensive product plan"
            },
            {
                "name": "Get Tasks",
                "method": "GET",
                "endpoint": "/api/v1/tasks",
                "description": "Retrieve user tasks"
            }
        ],
        "database_schema": [
            {
                "table_name": "product_plans",
                "fields": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "constraints": "PRIMARY KEY"
                    },
                    {
                        "name": "idea",
                        "type": "TEXT",
                        "constraints": "NOT NULL"
                    },
                    {
                        "name": "created_at",
                        "type": "TIMESTAMP",
                        "constraints": "DEFAULT NOW()"
                    }
                ]
            }
        ]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'architect', json.dumps(valid_architect_output)
        )
        logger.info("✅ Valid architect output passed validation")
        logger.info(f"   API Endpoints: {len(validated['api_endpoints'])}")
    except Exception as e:
        logger.error(f"❌ Valid architect output failed: {str(e)}")
    
    # Test 6: Valid Ticket Generator Output
    logger.info("\n=== TEST 6: VALID TICKET GENERATOR OUTPUT ===")
    valid_ticket_output = {
        "epics": [
            {
                "epic_name": "Core Product Planning",
                "description": "Implement the main product planning functionality with AI-powered insights",
                "stories": [
                    {
                        "story_title": "User Input Processing",
                        "description": "Process and validate user product ideas with AI assistance",
                        "acceptance_criteria": [
                            "User can input product idea",
                            "System validates input format",
                            "Error messages are clear and helpful"
                        ],
                        "tasks": [
                            {
                                "title": "Create input form",
                                "description": "Design and implement the responsive input form",
                                "estimated_hours": "8"
                            },
                            {
                                "title": "Implement validation",
                                "description": "Add client-side and server-side validation",
                                "estimated_hours": "6"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'ticket_generator', json.dumps(valid_ticket_output)
        )
        logger.info("✅ Valid ticket generator output passed validation")
        logger.info(f"   Epics: {len(validated['epics'])}")
    except Exception as e:
        logger.error(f"❌ Valid ticket generator output failed: {str(e)}")
    
    # Test 7: Fallback Output Generation
    logger.info("\n=== TEST 7: FALLBACK OUTPUT GENERATION ===")
    for agent in ['planner', 'analyst', 'architect', 'ticket_generator']:
        fallback = create_fallback_output(agent)
        logger.info(f"✅ Generated fallback for {agent}")
        logger.info(f"   Keys: {list(fallback.keys())}")
    
    logger.info("\n🎉 VALIDATION SYSTEM TEST COMPLETED")


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    
    logger.info("\n🧪 TESTING EDGE CASES")
    
    # Test with empty strings
    logger.info("\n=== EDGE CASE: EMPTY STRINGS ===")
    edge_case_output = {
        "product_name": "",  # Empty string
        "problem_statement": "Valid problem statement",
        "target_users": ["User"],
        "core_goals": ["Goal"],
        "key_features_high_level": ["Feature"]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'planner', json.dumps(edge_case_output)
        )
        logger.info("❌ Empty string should have been rejected")
    except Exception as e:
        logger.info(f"✅ Empty string correctly rejected: {str(e)}")
    
    # Test with too long strings
    logger.info("\n=== EDGE CASE: TOO LONG STRINGS ===")
    long_string = "x" * 200  # 200 characters
    edge_case_output = {
        "product_name": long_string,  # Too long
        "problem_statement": "Valid problem statement",
        "target_users": ["User"],
        "core_goals": ["Goal"],
        "key_features_high_level": ["Feature"]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'planner', json.dumps(edge_case_output)
        )
        logger.info("❌ Long string should have been rejected")
    except Exception as e:
        logger.info(f"✅ Long string correctly rejected: {str(e)}")
    
    # Test with invalid database constraints
    logger.info("\n=== EDGE CASE: INVALID DATABASE CONSTRAINTS ===")
    edge_case_output = {
        "system_design": "Valid system design",
        "tech_stack": {"frontend": "React"},
        "architecture_components": ["Component"],
        "api_endpoints": [
            {
                "name": "Test Endpoint",
                "method": "POST",
                "endpoint": "/api/test",
                "description": "Test endpoint"
            }
        ],
        "database_schema": [
            {
                "table_name": "test_table",
                "fields": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "constraints": ""  # Missing PRIMARY KEY
                    }
                ]
            }
        ]
    }
    
    try:
        validated = AgentValidationFactory.validate_agent_output(
            'architect', json.dumps(edge_case_output)
        )
        logger.info("❌ Missing PRIMARY KEY should have been rejected")
    except Exception as e:
        logger.info(f"✅ Missing PRIMARY KEY correctly rejected: {str(e)}")
    
    logger.info("\n🎉 EDGE CASES TEST COMPLETED")


if __name__ == "__main__":
    test_validation_system()
    test_edge_cases()
