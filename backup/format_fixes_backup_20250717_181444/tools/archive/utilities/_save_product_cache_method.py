# Method to add to PassiveExtractionWorkflow class
def _save_product_cache(self):
    """
    Save current supplier products to cache - placeholder for periodic saves.
    This method ensures the supplier cache is preserved during periodic saves.
    """
    try:
        # For now, this is a placeholder since supplier cache saving
        # is handled by _save_products_to_cache in the main workflow
        # This method is called during periodic saves but doesn't need
        # to do additional work unless we have specific supplier data to save
        log.info("Product cache save checkpoint - handled by main workflow")
        
        # In the future, if we need to save specific supplier data here,
        # we can implement it using the existing _save_products_to_cache pattern:
        # supplier_name = "clearance-king.co.uk"  # or get from context
        # supplier_cache_file_path = os.path.join(
        #     self.supplier_cache_dir, 
        #     f"{supplier_name.replace('.', '_')}_products_cache.json"
        # )
        # self._save_products_to_cache(current_products, supplier_cache_file_path)
        
    except Exception as e:
        log.error(f"Error in _save_product_cache: {e}")