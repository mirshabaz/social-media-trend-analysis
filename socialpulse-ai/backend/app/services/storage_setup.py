from app.services.cloud_storage import ensure_private_buckets


if __name__ == "__main__":
	created = ensure_private_buckets()
	if created:
		print("Created private Supabase Storage buckets: " + ", ".join(created))
	else:
		print("Both configured private Supabase Storage buckets already exist.")
