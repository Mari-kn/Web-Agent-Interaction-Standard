## 1. Core Scope Definitions (pod/scopes.py)

- [ ] 1.1 Add Education scope constants (COURSE_BROWSE, COURSE_ENROLL, COURSE_DROP, ASSIGNMENT_SUBMIT, GRADES_ACCESS, CERTIFICATE_REQUEST)
- [ ] 1.2 Add Real Estate scope constants (LISTING_BROWSE, LISTING_COMPARE, TOUR_SCHEDULE, APPLICATION_SUBMIT, LEASE_SIGN, MAINTENANCE_REQUEST)
- [ ] 1.3 Add Social Media scope constants (CONTENT_READ, CONTENT_CREATE, CONTENT_DELETE, PROFILE_MODIFY, MESSAGING_READ, MESSAGING_SEND, ACCOUNT_SETTINGS)
- [ ] 1.4 Add IoT scope constants (DEVICE_READ, DEVICE_CONTROL, AUTOMATION_MANAGE, FIRMWARE_UPDATE, ACCESS_GRANT, DEVICE_REMOVE)
- [ ] 1.5 Add risk level mappings for all 25 new scopes to RISK_LEVELS dict
- [ ] 1.6 Add convenience methods: education_read(), education_full(), realestate_full(), social_full(), iot_full()

## 2. Spec Document (spec/WAIS-Spec-Draft-v0.1.md)

- [ ] 2.1 Add section 8.6 Education scope table
- [ ] 2.2 Add section 8.7 Real Estate scope table
- [ ] 2.3 Add section 8.8 Social Media & Content scope table
- [ ] 2.4 Add section 8.9 IoT & Smart Home scope table
- [ ] 2.5 Add section 9.5 Education use case narrative
- [ ] 2.6 Add section 9.6 Real Estate use case narrative
- [ ] 2.7 Add section 9.7 Social Media use case narrative
- [ ] 2.8 Add section 9.8 IoT use case narrative

## 3. README (README.md)

- [ ] 3.1 Add Education scope table after Healthcare section
- [ ] 3.2 Add Real Estate scope table
- [ ] 3.3 Add Social Media & Content scope table
- [ ] 3.4 Add IoT & Smart Home scope table

## 4. Tests (tests/test_scopes.py)

- [ ] 4.1 Add tests for Education scope risk levels and convenience methods
- [ ] 4.2 Add tests for Real Estate scope risk levels and convenience methods
- [ ] 4.3 Add tests for Social Media scope risk levels and convenience methods
- [ ] 4.4 Add tests for IoT scope risk levels and convenience methods
- [ ] 4.5 Add tests for is_high_risk() with new high/critical scopes
