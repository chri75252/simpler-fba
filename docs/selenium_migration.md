# Selenium Migration Guide

This document summarizes the key changes required to migrate the Amazon FBA Agent System from Playwright to Selenium within the Codex environment.

## Playwright → Selenium Mapping

| Playwright Method | Selenium Equivalent |
|-------------------|---------------------|
| `page.click(selector)` | `driver.find_element(By.CSS_SELECTOR, selector).click()` |
| `page.fill(selector, text)` | `element = driver.find_element(By.CSS_SELECTOR, selector); element.clear(); element.send_keys(text)` |
| `page.text_content(selector)` | `driver.find_element(By.CSS_SELECTOR, selector).text` |
| `page.goto(url)` | `driver.get(url)` |
| `page.wait_for_selector(selector)` | `WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))` |
| `page.screenshot(path=...)` | `driver.save_screenshot(path)` |

## Error Handling Patterns

- **Element not found**: catch `NoSuchElementException` and retry or log a warning.
- **Timeouts**: catch `TimeoutException` from `WebDriverWait` and handle gracefully by returning failure states.
- **Stale elements**: catch `StaleElementReferenceException` and re-locate the element before interacting.

## Testing Framework

Basic import tests have been added under `tests/test_selenium_modules.py` to ensure the new modules are importable. When Chrome and Chromedriver are available the `SeleniumBrowserManager` can be instantiated and used in integration tests.

## Performance Tips

1. Use `undetected-chromedriver` in headless mode to reduce detection likelihood while keeping resource usage low.
2. Reuse a single browser instance across tasks to minimise startup overhead.
3. Employ explicit waits (`WebDriverWait`) instead of fixed `time.sleep` delays wherever possible.
