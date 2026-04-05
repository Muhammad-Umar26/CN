import random

class DNSMessage:
    def __init__(self, domain_name, is_query=True, transaction_id=None, recursion_desired=True, is_authoritative=False):
        self.identification = transaction_id if transaction_id else random.randint(1, 65535) 
        
        self.qr_flag = "Query" if is_query else "Reply"
        self.rd_flag = "Recursion Desired" if recursion_desired else "No Recursion"
        self.ra_flag = "Recursion Available" # Server supports it
        self.aa_flag = "Authoritative Reply" if is_authoritative else "Non-Authoritative"
        
        self.questions = [domain_name]
        self.answers = []
        self.authority = []
        self.additional = []

    def print_records(self):
        print("\n--- DNS MESSAGE ---")
        print(f"Transaction ID: {self.identification}")
        print(f"Flags: [{self.qr_flag} | {self.rd_flag} | {self.ra_flag} | {self.aa_flag}]")
        print(f"Questions: {self.questions[0]}")
        
        if self.qr_flag == "Reply":
            print(f"A: {', '.join(self.answers)}")
            print(f"NS: {', '.join(self.authority)}")
            print(f"MX: {', '.join(self.additional)}")
        print("-------------------\n")


# ==========================================
# PART 2: THE DATABASES (SERVERS)
# ==========================================
root_server = {
    ".com": "TLD_COM_SERVER",
    ".edu": "TLD_EDU_SERVER",
}

tld_com_server = {
    "google.com": "AUTH_GOOGLE_SERVER",
    "yahoo.com": "AUTH_YAHOO_SERVER"
}

tld_edu_server = {
    "mit.edu": "AUTH_MIT_SERVER",
    "stanford.edu": "AUTH_STANFORD_SERVER"
}

auth_servers_map = {
    "AUTH_GOOGLE_SERVER": {
        "A": ["64.233.187.99", "72.14.207.99", "64.233.167.99"],
        "NS": ["ns1.google.com.", "ns2.google.com.", "ns3.google.com.", "ns4.google.com."],
        "MX": ["10 smtp4.google.com.", "10 smtp1.google.com.", "10 smtp2.google.com."]
    },
    "AUTH_YAHOO_SERVER": {
        "A": ["74.6.143.25", "74.6.143.26"],
        "NS": ["ns1.yahoo.com.", "ns2.yahoo.com."],
        "MX": ["1 mta5.am0.yahoodns.net.", "1 mta6.am0.yahoodns.net."]
    },
    "AUTH_MIT_SERVER": {
        "A": ["18.9.22.69"],
        "NS": ["ns1.mit.edu.", "ns2.mit.edu.", "ns3.mit.edu."],
        "MX": ["10 mit-edu.mail.protection.outlook.com."]
    }
}

# ==========================================
# PART 3: CACHE & AUTO-FLUSH LOGIC
# ==========================================
local_cache = {}
CACHE_MAX_SIZE = 2 

def check_cache(domain):
    if domain in local_cache:
        print(f"\n[CACHE HIT] Found {domain} in local memory! Skipping network lookup.")
        return local_cache[domain]
    else:
        print(f"\n[CACHE MISS] {domain} not in cache. Starting DNS resolution...")
        return None

def add_to_cache(domain, records):
    global local_cache
    if len(local_cache) >= CACHE_MAX_SIZE:
        print("\n[WARNING] Cache limit reached! Auto-flushing memory...")
        local_cache.clear()
    local_cache[domain] = records
    print(f"[*] Added {domain} to local cache.")


# ==========================================
# PART 4: RESOLUTION LOGIC (Iterative & Recursive)
# ==========================================
def iterative_lookup(domain):
    print("--- Starting ITERATIVE Resolution ---")
    parts = domain.split('.')
    tld = "." + parts[-1]
    
    # 1. Local Server calls Root directly
    print("-> Local Server asking Root...")
    tld_server = root_server.get(tld)
    if not tld_server: return None
    print(f"<- Root replies to Local: Go ask {tld_server}")
    
    # 2. Local Server calls TLD directly
    print(f"-> Local Server asking {tld_server}...")
    active_tld = tld_com_server if tld == ".com" else tld_edu_server
    auth_server = active_tld.get(domain)
    if not auth_server: return None
    print(f"<- TLD replies to Local: Go ask {auth_server}")
    
    # 3. Local Server calls Authoritative directly
    print(f"-> Local Server asking {auth_server}...")
    records = auth_servers_map.get(auth_server)
    print("<- Authoritative replies to Local with records")
    
    return records

def recursive_lookup(domain):
    print("--- Starting RECURSIVE Resolution ---")
    parts = domain.split('.')
    tld = "." + parts[-1]
    
    print("-> 1. Local Server asks Root...")
    if tld not in root_server: return None
    tld_server = root_server[tld]
    
    print(f"   -> 2. Root asks {tld_server}...")
    active_tld = tld_com_server if tld == ".com" else tld_edu_server
    if domain not in active_tld: return None
    auth_server = active_tld[domain]
    
    print(f"      -> 3. TLD asks {auth_server}...")
    records = auth_servers_map.get(auth_server)
    
    print("      <- Authoritative replies to TLD")
    print("   <- TLD replies to Root")
    print("<- Root replies to Local Server")
    return records

# Function 3: The end of the chain
def call_authoritative_server(domain, auth_server):
    print(f"      -> 3. TLD asking {auth_server}...")
    records = auth_servers_map.get(auth_server)
    print("      <- Authoritative replies to TLD with records")
    return records

# Function 2: TLD calls Authoritative
def call_tld_server(domain, tld, tld_server):
    print(f"   -> 2. Root asking {tld_server}...")
    active_tld = tld_com_server if tld == ".com" else tld_edu_server
    auth_server = active_tld.get(domain)
    
    if not auth_server: return None
    
    # The TLD server calls the Auth server!
    records = call_authoritative_server(domain, auth_server)
    print("   <- TLD replies to Root with records")
    return records

# Function 1: Root calls TLD
def call_root_server(domain):
    print("-> 1. Local Server asking Root...")
    parts = domain.split('.')
    tld = "." + parts[-1]
    tld_server = root_server.get(tld)
    
    if not tld_server: return None
    
    # The Root server calls the TLD server!
    records = call_tld_server(domain, tld, tld_server)
    print("<- Root replies to Local Server with records")
    return records

def recursive_lookup(domain):
    print("--- Starting RECURSIVE Resolution ---")
    # Local server just kicks off the chain by calling Root
    return call_root_server(domain)


# ==========================================
# MAIN DRIVER FUNCTION
# ==========================================
def resolve_dns(domain, recursion_desired):
    print(f"\n========== Requesting: {domain} ==========")
    
    # Create the Query Message with the requested flag
    query_msg = DNSMessage(domain, is_query=True, recursion_desired=recursion_desired)
    transaction_id = query_msg.identification
    print("-> Sending DNS Query...")
    query_msg.print_records()
    
    # Check Cache (Satisfies the caching requirement for both modes)
    records = check_cache(domain)
    
    if records:
        print("-> Serving from Cache:")
        response_msg = DNSMessage(domain, is_query=False, transaction_id=transaction_id, recursion_desired=recursion_desired, is_authoritative=False)
        response_msg.answers = records.get("A", [])
        response_msg.authority = records.get("NS", [])
        response_msg.additional = records.get("MX", [])
        response_msg.print_records()
        return

    # Route to Iterative or Recursive based on the flag!
    if recursion_desired:
        fetched_records = recursive_lookup(domain)
    else:
        fetched_records = iterative_lookup(domain)
    
    if not fetched_records:
        print("[ERROR] Domain resolution failed.")
        return
    
    # Create Final Reply
    response_msg = DNSMessage(domain, is_query=False, transaction_id=transaction_id, recursion_desired=recursion_desired, is_authoritative=True)
    response_msg.answers = fetched_records.get("A", [])
    response_msg.authority = fetched_records.get("NS", [])
    response_msg.additional = fetched_records.get("MX", [])
    
    print(f"\n{domain}/{fetched_records['A'][0]}")
    response_msg.print_records()
    add_to_cache(domain, fetched_records)

# # ==========================================
# # RUNNING THE DEMO
# # ==========================================
# if __name__ == "__main__":
#     # Test 1: Recursive lookup (Matches left side of Figure 01)
#     resolve_dns("google.com", recursion_desired=True)
    
#     # Test 2: Caching of a recursive lookup
#     resolve_dns("google.com", recursion_desired=True)
    
#     # Test 3: Iterative lookup (Matches right side of Figure 01)
#     resolve_dns("yahoo.com", recursion_desired=False)

# ==========================================
# RUNNING THE DEMO
# ==========================================
if __name__ == "__main__":
    # Test 1: Query a .com domain
    resolve_dns("google.com", True)
    
    # Test 2: Query a .edu domain
    resolve_dns("mit.edu", False)
    
    # Test 3: Query MIT again to show the Cache Hit working 
    # (Notice the Query ID and Response ID match beautifully!)
    resolve_dns("google.com", True)
    
    # Test 4: Query Stanford (Will hit limit and auto-flush cache)
    resolve_dns("stanford.edu", True)

    resolve_dns("yahoo.com", False)

    resolve_dns("google.com", True)