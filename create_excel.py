import pandas as pd

# Create test phone numbers
numbers = {
    'Telefon': [
        '905051430606',
        '0505 143 06 06',
        '5051430606',
        '+905051430606',
        '90-505-143-0606',
        '123456',
        '+1234567890',
        '0555-444-3322',
        '5554443322'
    ]
}

# Create DataFrame
df = pd.DataFrame(numbers)

# Save to Excel
df.to_excel('test_numbers.xlsx', index=False) 