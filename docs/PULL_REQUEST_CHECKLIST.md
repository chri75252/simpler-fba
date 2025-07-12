# Pull Request Checklist - Amazon FBA Agent System v3.5

**Version:** 3.5 Enterprise Development Standards  
**Purpose:** Quality assurance checklist for all future refactors and improvements  
**Last Updated:** 2025-06-15

## 🎯 Pre-Development Checklist

### 📋 Planning and Design
- [ ] **Requirement Analysis**
  - [ ] User story/requirement clearly defined
  - [ ] Acceptance criteria documented  
  - [ ] Impact assessment completed (security, performance, compatibility)
  - [ ] Architecture review for changes affecting core workflow

- [ ] **Design Review**
  - [ ] Technical design document created (for major changes)
  - [ ] Database schema changes reviewed (if applicable)
  - [ ] API contract changes documented (if applicable)
  - [ ] Security implications assessed

### 🔧 Development Environment
- [ ] **Environment Setup**
  - [ ] Latest code pulled from main branch
  - [ ] Python dependencies up to date (`pip install -r requirements.txt`)
  - [ ] Chrome debug port available (port 9222)
  - [ ] OpenAI API key set in environment variables (never hardcoded)
  - [ ] Development database/cache cleared if needed

## 🚨 Critical Security Checklist

### 🔐 Security Validation (MANDATORY)
- [ ] **API Key Management**
  - [ ] NO hardcoded API keys in any files
  - [ ] All secrets use environment variables (`os.getenv()`)
  - [ ] Secrets validation implemented (key format, existence)
  - [ ] `.env.example` file updated with new variables

- [ ] **Input Validation**
  - [ ] All external inputs validated (ASIN, URLs, scraped data)
  - [ ] SQL injection prevention (if database queries added)
  - [ ] XSS prevention for any web interfaces
  - [ ] File path validation for cache operations

- [ ] **Security Scanning**
  ```bash
  # Run before every PR
  python -m bandit -r tools/ config/
  grep -r "sk-" tools/ config/  # Should return no results
  grep -r "api_key.*=" tools/ config/  # Check for hardcoded keys
  ```

## 🧪 Testing Requirements

### ✅ Automated Testing
- [ ] **Unit Tests**
  - [ ] New functions have unit tests
  - [ ] Existing tests still pass
  - [ ] Test coverage >80% for new code
  - [ ] Edge cases covered (empty inputs, network failures, rate limits)

- [ ] **Integration Tests**  
  - [ ] End-to-end workflow test passes
  - [ ] AI fallback system tested across all tiers
  - [ ] Cache persistence tested
  - [ ] Amazon matching accuracy validated

- [ ] **Test Execution**
  ```bash
  # Required test commands
  python -m pytest tests/ -v
  python -m pytest --cov=tools tests/
  python tools/passive_extraction_workflow_latest.py --health-check
  ```

### 🔄 Manual Testing
- [ ] **Core Functionality**
  - [ ] Main workflow executes without errors
  - [ ] AI category selection working (>95% success rate)
  - [ ] Product matching accuracy maintained (>85%)
  - [ ] Financial calculations accurate
  - [ ] Cache files generated correctly

- [ ] **Error Handling**
  - [ ] Graceful handling of network timeouts
  - [ ] Proper error logging (no silent failures)
  - [ ] Recovery from corrupted cache files
  - [ ] Browser automation failures handled

- [ ] **Performance Testing**
  - [ ] No significant performance regression
  - [ ] Memory usage within expected bounds (<3GB)
  - [ ] Processing speed maintained (2-3 products/minute)

## 📊 Code Quality Standards

### 🎨 Code Style and Structure
- [ ] **Python Standards**
  - [ ] PEP 8 compliance checked with `flake8`
  - [ ] Code formatted with `black`
  - [ ] Type hints added for new functions
  - [ ] Docstrings for all new classes and functions

- [ ] **Architecture Compliance**
  - [ ] No new monolithic functions (>100 lines)
  - [ ] Proper separation of concerns
  - [ ] No circular imports
  - [ ] Error handling consistent with existing patterns

- [ ] **Code Quality Tools**
  ```bash
  # Required quality checks
  python -m flake8 tools/ --max-line-length=88
  python -m black tools/ --check
  python -m pylint tools/ --fail-under=8.0
  python -m mypy tools/ --ignore-missing-imports
  ```

### 📝 Documentation Updates
- [ ] **Code Documentation**
  - [ ] Inline comments for complex logic
  - [ ] Function docstrings with parameters and return types
  - [ ] Class docstrings with purpose and usage examples
  - [ ] Type hints for all new functions

- [ ] **System Documentation**
  - [ ] README.md updated (if user-facing changes)
  - [ ] SYSTEM_DEEP_DIVE.md updated (if architecture changes)
  - [ ] Configuration documentation updated (if config changes)
  - [ ] API documentation updated (if interface changes)

## 🔧 Configuration and Deployment

### ⚙️ Configuration Management
- [ ] **Configuration Updates**
  - [ ] New configuration options documented
  - [ ] Default values provided and tested
  - [ ] Configuration validation implemented
  - [ ] Backward compatibility maintained

- [ ] **Environment Configuration**
  - [ ] Development environment tested
  - [ ] Production configuration reviewed
  - [ ] Environment variable documentation updated

### 🚀 Deployment Readiness
- [ ] **Deployment Checklist**
  - [ ] Migration scripts provided (if database changes)
  - [ ] Rollback plan documented
  - [ ] Dependencies updated in requirements.txt
  - [ ] Docker configuration updated (if applicable)

## 📈 Performance and Monitoring

### ⚡ Performance Validation
- [ ] **Performance Benchmarks**
  - [ ] Benchmark tests run and results documented
  - [ ] No significant performance degradation
  - [ ] Memory usage profiled and acceptable
  - [ ] API call rates within limits

- [ ] **Scalability Considerations**
  - [ ] Changes tested with larger datasets
  - [ ] Concurrent access considerations (if applicable)
  - [ ] Cache size limits respected
  - [ ] Resource cleanup implemented

### 📊 Monitoring and Observability
- [ ] **Logging and Monitoring**
  - [ ] Appropriate log levels used
  - [ ] Error conditions logged with context
  - [ ] Performance metrics captured
  - [ ] Health check endpoints updated (if applicable)

## 🔄 CI/CD Pipeline

### 🤖 Automated Checks
- [ ] **Pre-commit Hooks**
  ```bash
  # Install pre-commit hooks
  pip install pre-commit
  pre-commit install
  
  # Hooks should include:
  # - flake8 (code style)
  # - black (code formatting)  
  # - bandit (security scanning)
  # - pytest (automated tests)
  ```

- [ ] **GitHub Actions/CI**
  - [ ] All CI checks pass
  - [ ] Security scans pass
  - [ ] Test coverage requirements met
  - [ ] Build/deployment tests pass

### 📋 Review Process
- [ ] **Code Review Requirements**
  - [ ] At least 2 approving reviewers
  - [ ] Security team approval (for security-related changes)
  - [ ] Architecture team approval (for major changes)
  - [ ] All review comments addressed

## 🚨 Critical Issue Prevention

### 🛑 Never Allow These in PR
- [ ] **Security Anti-Patterns**
  - ❌ Hardcoded API keys, passwords, or secrets
  - ❌ Unvalidated user inputs
  - ❌ SQL queries without parameterization
  - ❌ File operations without path validation

- [ ] **Code Anti-Patterns**
  - ❌ Functions longer than 100 lines
  - ❌ Silent exception handling (`except: pass`)
  - ❌ Global variables for application state
  - ❌ Infinite loops without break conditions

- [ ] **Performance Anti-Patterns**
  - ❌ Blocking operations in async code
  - ❌ Loading entire large files into memory
  - ❌ N+1 database/API query patterns
  - ❌ Memory leaks (unclosed resources)

## 📋 Release Types and Requirements

### 🔧 Patch Release (Bug Fixes)
**Requirements:**
- [ ] Bug reproduction test case added
- [ ] Fix tested in isolation
- [ ] No breaking changes
- [ ] Minimal code changes
- [ ] Documentation updated if user-facing

### ⭐ Minor Release (New Features)
**Requirements:**
- [ ] Feature flag implemented (if applicable)
- [ ] Comprehensive testing suite
- [ ] Performance impact assessed
- [ ] Documentation thoroughly updated
- [ ] Migration path documented

### 🚀 Major Release (Breaking Changes)
**Requirements:**
- [ ] Breaking changes clearly documented
- [ ] Migration guide provided
- [ ] Backward compatibility plan
- [ ] Extended testing period
- [ ] Stakeholder approval obtained

## 🎯 Definition of Done

### ✅ Code Complete Criteria
A pull request is considered complete when ALL of the following are true:

1. **✅ Security:** No hardcoded secrets, all inputs validated
2. **✅ Quality:** Code style compliant, >80% test coverage
3. **✅ Functionality:** All acceptance criteria met, manual testing passed
4. **✅ Performance:** No significant regressions, benchmarks within limits
5. **✅ Documentation:** All relevant docs updated and accurate
6. **✅ Testing:** Automated tests pass, edge cases covered
7. **✅ Review:** At least 2 approving reviews, all comments resolved
8. **✅ Deployment:** Ready for production, rollback plan exists

### 🚫 Common Rejection Criteria
PRs will be rejected for:
- Hardcoded API keys or secrets
- Missing or insufficient tests
- Significant performance regressions
- Breaking existing functionality
- Poor code quality (style, structure)
- Insufficient documentation
- Security vulnerabilities

## 🛠️ Tools and Scripts

### 📜 Pre-PR Validation Script
```bash
#!/bin/bash
# pre_pr_check.sh - Run before creating PR

echo "🔍 Running pre-PR validation..."

# Security check
echo "🔐 Security validation..."
python -m bandit -r tools/ config/ || exit 1
if grep -r "sk-" tools/ config/; then
    echo "❌ Hardcoded API keys found!"
    exit 1
fi

# Code quality
echo "🎨 Code quality checks..."
python -m flake8 tools/ --max-line-length=88 || exit 1
python -m black tools/ --check || exit 1

# Testing
echo "🧪 Running tests..."
python -m pytest tests/ -v || exit 1
python -m pytest --cov=tools tests/ --cov-fail-under=80 || exit 1

# Health check
echo "🏥 System health check..."
python tools/passive_extraction_workflow_latest.py --health-check || exit 1

echo "✅ All pre-PR checks passed!"
```

### 🔄 Post-Merge Validation
```bash
#!/bin/bash
# post_merge_validation.sh - Run after PR merge

echo "🚀 Post-merge validation..."

# Deployment test
python tools/passive_extraction_workflow_latest.py --max-products 5

# Performance benchmark
python tools/performance_benchmark.py

# Integration test
python tests/integration_test_full_workflow.py

echo "✅ Post-merge validation complete!"
```

## 📞 Support and Escalation

### 🆘 When to Seek Help
- Security vulnerabilities discovered
- Breaking changes to core architecture
- Performance regressions >20%
- Test failures in CI/CD pipeline
- Uncertain about API key management

### 📧 Contact Information
- **Security Issues:** security-team@company.com
- **Architecture Questions:** architecture-team@company.com  
- **CI/CD Issues:** devops-team@company.com
- **Emergency:** On-call rotation

---

## 🎯 Summary
This checklist ensures that all future changes to the Amazon FBA Agent System v3.5 maintain the high quality, security, and performance standards established in the current architecture. Every PR must pass ALL applicable checks before merge approval.

**Remember:** Security is non-negotiable. Performance matters. Quality code is maintainable code.