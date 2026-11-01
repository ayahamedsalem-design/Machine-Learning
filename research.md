## 1. print() vs. logging

* **Difference:** `print()` simply outputs text to the console, while the `logging` module records events with rich metadata (timestamps, severity) and can route them to multiple destinations like files.
* **When to use:** Use `print()` for simple command-line scripts or quick, temporary debugging. Use `logging` for long-running applications, web services, and libraries.
* **Why logging is preferred in production:** It allows developers to filter messages by severity, persist records to files for later analysis, and maintain a historical trail without disrupting the user interface.

## 2. Logging Levels

Python uses five standard severity levels to categorize log messages:

* **DEBUG:** Detailed information used primarily for diagnosing problems. 
    - Example: Outputting the exact state of variables inside a loop.
* **INFO:** Confirmation that the application is working as expected. 
    - Example: "App successfully started."
* **WARNING:** An indication that something unexpected occurred, but the software is still functioning. 
    - Example: "Disk space is running low."
* **ERROR:** A serious problem that prevented the software from performing a specific function. 
    - Example: "Failed to connect to the database."
* **CRITICAL:** A severe error indicating the program itself may crash or stop running entirely. 
    - Example: "Out of memory."

## 3. Log Messages

* **Definition:** A log message is a single formatted text record describing a specific event that occurred while a program was running.
* **Useful contents:** A good log message includes a timestamp, the level, the module name, the line number, and a clear description of the event with relevant contextual data like a User ID.
* **Debugging value:** Log messages create a chronological path, allowing developers to reconstruct the exact state and sequence of events leading up to a crash without needing to replicate the bug live.

## 4. Logging Configuration

Python's `logging.basicConfig()` function provides a quick way to configure the default behavior of the logging system.

* **filename:** Specifies the name of the file where log messages should be saved instead of printing them to the console.
* **level:** Sets the minimum severity threshold for the root logger. If set to `logging.INFO`, all `DEBUG` messages are ignored.
* **format:** Defines the string layout of the log message, allowing you to inject variables like `%(levelname)s` and `%(message)s`.
* **datefmt:** Customizes the visual format of the timestamp used in the log string, using standard time formatting codes like `%Y-%m-%d %H:%M:%S`.