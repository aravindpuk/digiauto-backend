from django.db import models


class Complaint(models.Model):
    text = models.CharField(max_length=500, unique=True)
    def __str__(self): return self.text


class VehicleMake(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name


class VehicleModel(models.Model):
    name    = models.CharField(max_length=100)
    fkMaker = models.ForeignKey(VehicleMake, on_delete=models.CASCADE,
                                related_name="models")
    class Meta:
        unique_together = ("name", "fkMaker")
    def __str__(self): return f"{self.fkMaker.name} {self.name}"


class Vehicle(models.Model):
    vehicle_number = models.CharField(max_length=20)
    vehicle_model  = models.ForeignKey(VehicleModel, on_delete=models.SET_NULL,
                                       null=True, blank=True)
    user           = models.ForeignKey("user.User", on_delete=models.CASCADE)
    year           = models.CharField(max_length=4,  blank=True, default="")
    chassis_number = models.CharField(max_length=50, blank=True, default="")
    engine_number  = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        unique_together = ("vehicle_number", "user")
    def __str__(self): return self.vehicle_number


class JobStatus(models.Model):
    name  = models.CharField(max_length=50, unique=True)
    order = models.IntegerField(default=0)   # 0=pending 1=active 2=completed 3=delivered
    def __str__(self): return self.name


class JobCard(models.Model):
    branch     = models.ForeignKey("garage.Branch", on_delete=models.CASCADE)
    created_by = models.ForeignKey("user.User", on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name="Job_creator")
    complaints = models.ManyToManyField(Complaint, related_name="jobcards")
    vehicle    = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    kilometer  = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    mechanic   = models.ManyToManyField("user.User",
                                        related_name="job_mechanic", blank=True)
    status     = models.ForeignKey(JobStatus, on_delete=models.CASCADE)

    def job_id_display(self):
        return f"DIGI-J{str(self.id).zfill(2)}"

    def __str__(self):
        return self.job_id_display()


class JobCardSpare(models.Model):
    jobcard    = models.ForeignKey(JobCard, on_delete=models.CASCADE,
                                   related_name="spares")
    spare      = models.ForeignKey("spare.Spare", on_delete=models.CASCADE)
    quantity   = models.IntegerField()
    mrp        = models.DecimalField(max_digits=10, decimal_places=2)
    complaints = models.ManyToManyField(Complaint, related_name="spares",
                                        blank=True)
    def __str__(self): return f"{self.spare.partname} x{self.quantity}"


class JobCardLabour(models.Model):
    jobcard    = models.ForeignKey(JobCard, on_delete=models.CASCADE,
                                   related_name="labour_services")
    labour     = models.ForeignKey("labour.Labour", on_delete=models.CASCADE)
    technician = models.ForeignKey("user.User", on_delete=models.SET_NULL,
                                   null=True, blank=True)
    amount     = models.DecimalField(max_digits=10, decimal_places=2,
                                     default=0)   # ← new field
    complaints = models.ManyToManyField(Complaint, related_name="labours",
                                        blank=True)
    def __str__(self): return self.labour.name


class Invoice(models.Model):
    jobcard        = models.OneToOneField(JobCard, on_delete=models.CASCADE,
                                          related_name="invoice")
    invoice_number = models.CharField(max_length=50, unique=True)
    date           = models.DateField(auto_now_add=True)
    total_amount   = models.DecimalField(max_digits=12, decimal_places=2)
    paid           = models.BooleanField(default=False)
    def __str__(self): return f"Invoice {self.invoice_number}"