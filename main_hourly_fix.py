    # Initialize proxy
    logger.info("Initializing Oxylabs proxy...")
    proxy_manager = ProxyManager()
    
    # Always test proxy on startup or if it needs updating
    if not proxy_manager.proxy_working or proxy_manager.should_update_proxy_list():
        logger.info("Testing proxy connection...")
        if not proxy_manager.test_proxy_connection(max_retries=5):
            logger.error("❌ Proxy not working. Cannot proceed without proxy.")
            return False
    
    logger.info("✅ Proxy working")
