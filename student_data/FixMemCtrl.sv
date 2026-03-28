// Memory controller with 2-bank interleaving.
//
// Routes memory requests to one of two banks based on the least-significant
// address bit. Bank 0 handles even addresses, bank 1 handles odd addresses.
// Each bank has a 1-cycle latency. The controller tracks which bank a
// pending request went to and returns the corresponding bank's data.
//
// Architecture:
//   - req/addr/wdata: request interface (active-high req, address, write data)
//   - bank: combinationally selected from addr[0]
//   - bank0_req/bank1_req: per-bank request signals
//   - bank0_data/bank1_data: per-bank read data (modeled as simple registers)
//   - pending[0], pending[1]: tracks in-flight requests per bank
//   - resp_bank: remembers which bank the oldest pending request targets
//   - rdata: output, returns data from the correct bank on response
//   - resp_valid: output, high when a response is available
module mem_ctrl(
  input         clk,
  input         reset,
  input         req,
  input  [7:0]  addr,
  input  [7:0]  wdata,
  output reg [7:0] rdata,
  output reg       resp_valid
);
  reg [7:0] bank0_data, bank1_data;
  reg       bank;
  reg       pending0, pending1;
  reg       resp_bank;
  reg [7:0] addr_r;

  initial begin
    bank0_data = 0; bank1_data = 0;
    bank = 0; pending0 = 0; pending1 = 0;
    resp_bank = 0; addr_r = 0;
    rdata = 0; resp_valid = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      bank0_data <= 0; bank1_data <= 0;
      bank <= 0; pending0 <= 0; pending1 <= 0;
      resp_bank <= 0; addr_r <= 0;
      rdata <= 0; resp_valid <= 0;
    end else begin
      // Latch address and compute bank select
      addr_r <= addr;
      bank   <= addr[0];

      // Route request to banks
      pending0 <= req && bank == 1'b0; // HINT: check this line carefully
      pending1 <= req && bank == 1'b1;

      // Bank storage: write on request
      if (req && addr[0] == 1'b0) begin
        bank0_data <= wdata;
      end
      if (req && addr[0] == 1'b1) begin
        bank1_data <= wdata;
      end

      // Track which bank to read response from
      resp_bank <= addr[1]; // HINT: check this line carefully

      // Response: return data from the correct bank
      if (pending0 || pending1) begin
        resp_valid <= 1'b1;
        if (resp_bank == 1'b0) begin
          rdata <= bank0_data;
        end else begin
          rdata <= 8'd0;
        end
      end else begin
        resp_valid <= 1'b0;
      end
    end
  end

  p_reset:       assert property (@(posedge clk) reset |=> !resp_valid && !pending0 && !pending1);
  p_bank_select: assert property (@(posedge clk) !reset && req |=> bank == $past(addr[0]));
  p_bank0_route: assert property (@(posedge clk) !reset && req && addr[0] == 1'b0 |=> pending0);
  p_bank1_route: assert property (@(posedge clk) !reset && req && addr[0] == 1'b1 |=> pending1);
  p_resp_order:  assert property (@(posedge clk) !reset && req && addr[0] == 1'b0 |=> ##1 resp_bank == 1'b0);
  p_no_drop:     assert property (@(posedge clk) !reset && (pending0 || pending1) |=> resp_valid);
  p_data_match:  assert property (@(posedge clk) !reset && resp_valid && resp_bank == 1'b1 |-> rdata == bank1_data);
endmodule
