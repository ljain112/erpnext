import frappe
from frappe import _
from frappe.utils import getdate


class TaxWithholdingController:
	def __init__(self, doc):
		self.doc = doc
		self.posting_date = doc.posting_date
		self.company = doc.company

	def set_tax_withholding(self):
		pass

	def validate_tax_withholding(self):
		pass

	def apply_tds(self):
		self.get_tax_withhold_details()
		self.update_tax_withholding_taxes()

	def get_tax_withhold_details(self):
		self.tax_withheld_details = frappe._dict()

		self.get_category_wise_tax_details()

		return self.tax_withheld_details

	def get_tax_withholding_categories(self):
		# currently only one category is supported in the ERPNext
		return self.doc.tax_withholding_category

	def get_category_wise_tax_details(self):
		"""
		Get tax withheld rows for each category
		tax_withheld_details = [{
		"posting_date": "",
		"company": "",
		"account": "",
		"party_type"",
		"party"",
		"voucher_type"",
		"voucher_no": "",
		"tax_withholding_category: "",
		"base_tax_withholding_net_total": "",
		"rate: "",
		"tax_amount": "",
		      ]}
		"""
		# currently only one category is supported in the ERPNext
		category_details = frappe._dict()

		for category in self.get_tax_withholding_categories():
			category_details.update(get_tax_withholding_details(category, self.posting_date, self.company))
			category_details.update(self.get_tax_withholding_net_total(category_details))
			self.tax_withheld_details.append(self.get_tds_detail(category_details))

	def get_tax_withholding_net_total(category_details):
		"""
		Based on Doctype and needs to be hookable
		"""

	def get_tds_detail(self, category_details):
		tds_deducted = is_tds_already_deducted(category_details, self.party_details)

		self.get_invoice_tds_details(category_details, self.party_details, tds_deducted)
		self.get_advance_tds_details(category_details, self.party_details, self.doc)
		self.get_ldc_tds_details(category_details, self.party_details)

		return self.tax_withheld_details

	def get_invoice_details(self, category_details):
		self.vouchers = frappe._dict()
		net_amount = 0

		self.get_current_invoice()
		self.get_pending_invoices()
		self.get_pending_payments()

		threshold = category_details.get("threshold", 0)
		cumulative_threshold = category_details.get("cumulative_threshold", 0)

		return (
			cumulative_threshold
			and net_amount >= cumulative_threshold
			or threshold
			and category_details.net_total >= threshold
		)

	def get_tax_row(self, tax_withheld_details, category_details):
		tax_row = frappe._dict(
			{
				"category": "Total",
				"charge_type": "Actual",
				"tax_amount": 0,
				"add_deduct_tax": "Add",
				"description": tax_withheld_details.tax_withholding_category,
				"account_head": category_details.account_head,
			}
		)
		for row in self.tax_withheld_details:
			tax_row.tax_amount += row.tax_amount

		tax_row.tax_amount = -1 * tax_row.tax_amount

		return tax_row


def is_tds_already_deducted(category_details, party_details):
	return frappe.db.exists(
		"Tax Withholding",
		{
			"party_type": party_details.party_type,
			"party": party_details.party,
			"tax_withholding_category": category_details.tax_withholding_category,
			"posting_date": [
				"between",
				(category_details.from_date, category_details.to_date),
			],
			"tax_amount": [">", 0],
		},
	)


def get_pending_tax_withholding(doc):
	pass


def get_tax_withholding_details(tax_withholding_category, posting_date, company):
	tax_withholding = frappe.get_doc("Tax Withholding Category", tax_withholding_category)

	tax_rate_detail = get_tax_withholding_rates(tax_withholding, posting_date)

	for account_detail in tax_withholding.accounts:
		if company == account_detail.company:
			return frappe._dict(
				{
					"tax_withholding_category": tax_withholding_category,
					"account_head": account_detail.account,
					"rate": tax_rate_detail.tax_withholding_rate,
					"from_date": tax_rate_detail.from_date,
					"to_date": tax_rate_detail.to_date,
					"threshold": tax_rate_detail.single_threshold,
					"cumulative_threshold": tax_rate_detail.cumulative_threshold,
					"description": (
						tax_withholding.category_name
						if tax_withholding.category_name
						else tax_withholding_category
					),
					"consider_party_ledger_amount": tax_withholding.consider_party_ledger_amount,
					"tax_on_excess_amount": tax_withholding.tax_on_excess_amount,
					"round_off_tax_amount": tax_withholding.round_off_tax_amount,
				}
			)


def get_tax_withholding_rates(tax_withholding, posting_date):
	# returns the row that matches with the fiscal year from posting date
	for rate in tax_withholding.rates:
		if getdate(rate.from_date) <= getdate(posting_date) <= getdate(rate.to_date):
			return rate

	frappe.throw(_("No Tax Withholding data found for the current posting date."))


def get_category_wise_details(doc):
	pass
