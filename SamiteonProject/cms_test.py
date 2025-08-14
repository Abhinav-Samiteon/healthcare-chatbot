curl -X 'GET' \
  'https://data.cms.gov/provider-data/api/1/datastore/sql?query=%5BSELECT%20%2A%20FROM%203f0c8811-d49a-5053-8ce1-49d20f9a2b87%5D%5BLIMIT%202%5D&show_db_columns=true' \
  -H 'accept: application/json'
Request URL
https://data.cms.gov/provider-data/api/1/datastore/sql?query=%5BSELECT%20%2A%20FROM%203f0c8811-d49a-5053-8ce1-49d20f9a2b87%5D%5BLIMIT%202%5D&show_db_columns=true
Server response
Code	Details
200	
Response body
Download
[
  {
    "record_number": "1",
    "npi": "1003000126",
    "ind_pac_id": "7517003643",
    "ind_enrl_id": "I20130530000085",
    "provider_last_name": "ENKESHAFI",
    "provider_first_name": "ARDALAN",
    "provider_middle_name": "",
    "suff": "",
    "gndr": "M",
    "cred": "MD",
    "med_sch": "OTHER",
    "grd_yr": "1994",
    "pri_spec": "HOSPITALIST",
    "sec_spec_1": "INTERNAL MEDICINE",
    "sec_spec_2": "",
    "sec_spec_3": "",
    "sec_spec_4": "",
    "sec_spec_all": "INTERNAL MEDICINE",
    "telehlth": "",
    "facility_name": "MEDICAL FACULTY ASSOCIATES, INC",
    "org_pac_id": "4082528898",
    "num_org_mem": "593",
    "adr_ln_1": "1200 PECAN ST SE",
    "adr_ln_2": "",
    "ln_2_sprs": "",
    "citytown": "WASHINGTON",
    "state": "DC",
    "zip_code": "20032",
    "telephone_number": "7714446200",
    "ind_assgn": "Y",
    "grp_assgn": "Y",
    "adrs_id": "DC200320000WA1200XSEXX400"
  },
  {
    "record_number": "6",
    "npi": "1003000126",
    "ind_pac_id": "7517003643",
    "ind_enrl_id": "I20231208000285",
    "provider_last_name": "ENKESHAFI",
    "provider_first_name": "ARDALAN",
    "provider_middle_name": "",
    "suff": "",
    "gndr": "M",
    "cred": "MD",
    "med_sch": "OTHER",
    "grd_yr": "1994",
    "pri_spec": "INTERNAL MEDICINE",
    "sec_spec_1": "",
    "sec_spec_2": "",
    "sec_spec_3": "",
    "sec_spec_4": "",
    "sec_spec_all": "",
    "telehlth": "",
    "facility_name": "GEISINGER CLINIC",
    "org_pac_id": "5395657001",
    "num_org_mem": "2983",
    "adr_ln_1": "400 HIGHLAND AVE",
    "adr_ln_2": "",
    "ln_2_sprs": "",
    "citytown": "LEWISTOWN",
    "state": "PA",
    "zip_code": "170441167",
    "telephone_number": "7172485411",
    "ind_assgn": "Y",
    "grp_assgn": "Y",
    "adrs_id": "PA170441167LE400XXAVEX300"
  }
]
Response headers
 accept-ranges: bytes 
 cache-control: max-age=0,no-cache,no-store 
 content-encoding: gzip 
 content-language: en 
 content-length: 555 
 content-type: application/json 
 date: Tue,12 Aug 2025 02:59:37 GMT 
 etag: "1754967577" 
 expires: Tue,12 Aug 2025 02:59:37 GMT 
 last-modified: Tue,12 Aug 2025 02:59:37 GMT 
 pragma: no-cache 
 strict-transport-security: max-age=31536000 ; includeSubDomains ; preload 
 vary: Cookie,Origin,Accept-Encoding 
 x-age: 0 
 x-ah-environment: prod 
 x-content-type-options: nosniff 
 x-drupal-cache: MISS 
 x-frame-options: SAMEORIGIN 
 x-generator: Drupal 10 (https://www.drupal.org) 
 x-request-id: v-61e776d6-7728-11f0-ac33-232975269dcb 
 x-xss-protection: 1; mode=block 